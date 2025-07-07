# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class EmployeePortalHub(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Enhanced portal home with employee-specific counters"""
        values = super()._prepare_home_portal_values(counters)

        if not request.env.user.employee_id:
            return values

        employee = request.env.user.employee_id

        # Always provide leave request count if the module is available
        try:
            if request.env['hr.leave'].check_access('read'):
                values['leave_request_count'] = request.env['hr.leave'].search_count([
                    ('employee_id.user_id', '=', request.env.user.id)
                ])
            else:
                values['leave_request_count'] = 0
        except:
            values['leave_request_count'] = 0

        # Add other counters when explicitly requested or when modules are available
        if 'payslip_count' in counters or 'hr.payslip' in request.env:
            try:
                values['payslip_count'] = request.env['hr.payslip'].search_count([
                    ('employee_id', '=', employee.id)
                ]) if 'hr.payslip' in request.env else 0
            except:
                values['payslip_count'] = 0

        if 'timesheet_count' in counters or 'account.analytic.line' in request.env:
            try:
                values['timesheet_count'] = request.env['account.analytic.line'].search_count([
                    ('user_id', '=', request.env.user.id)
                ]) if 'account.analytic.line' in request.env else 0
            except:
                values['timesheet_count'] = 0

        # Add quick stats for dashboard
        values.update({
            'employee': employee,
            'is_employee': True,
        })

        return values

    @http.route(['/my/dashboard'], type='http', auth="user", website=True)
    def employee_dashboard(self, **kw):
        """Main employee dashboard"""
        if not request.env.user.employee_id:
            return request.render("employee_portal_hub.no_employee_error")

        employee = request.env.user.employee_id

        # Get recent leave requests (if leave request module is available)
        recent_leaves = []
        try:
            recent_leaves = request.env['hr.leave'].search([
                ('employee_id.user_id', '=', request.env.user.id)
            ], limit=5, order='create_date desc')
        except:
            recent_leaves = []

        # Get recent timesheets (if timesheet module is available)
        recent_timesheets = []
        monthly_hours = 0
        has_project_access = False
        if 'account.analytic.line' in request.env:
            try:
                # Check if user has project access
                try:
                    request.env['project.project'].check_access('read')
                    has_project_access = True
                except:
                    has_project_access = False

                # Get timesheets
                all_timesheets = request.env['account.analytic.line'].search([
                    ('user_id', '=', request.env.user.id)
                ], limit=10, order='date desc')

                # Filter timesheets safely
                safe_timesheets = []
                for timesheet in all_timesheets:
                    try:
                        if has_project_access and timesheet.project_id:
                            safe_timesheets.append(timesheet)
                        elif not timesheet.project_id:
                            safe_timesheets.append(timesheet)
                        else:
                            safe_timesheets.append(timesheet)

                        if len(safe_timesheets) >= 5:
                            break
                    except:
                        continue

                recent_timesheets = safe_timesheets[:5]

                # Calculate monthly hours safely
                current_month = datetime.now().replace(day=1)
                try:
                    monthly_timesheets = request.env['account.analytic.line'].search([
                        ('user_id', '=', request.env.user.id),
                        ('date', '>=', current_month)
                    ])
                    monthly_hours = sum(monthly_timesheets.mapped('unit_amount'))
                except:
                    monthly_hours = 0
            except:
                recent_timesheets = []
                monthly_hours = 0

        # Get recent payslips (if payroll module is available)
        recent_payslips = []
        if 'hr.payslip' in request.env:
            try:
                recent_payslips = request.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id)
                ], limit=3, order='date_from desc')
            except:
                recent_payslips = []

        # Pending leave requests
        pending_leaves = 0
        try:
            pending_leaves = request.env['hr.leave'].search_count([
                ('employee_id.user_id', '=', request.env.user.id),
                ('state', 'in', ['draft', 'confirm'])
            ])
        except:
            pending_leaves = 0

        values = {
            'employee': employee,
            'recent_leaves': recent_leaves,
            'recent_timesheets': recent_timesheets,
            'recent_payslips': recent_payslips,
            'monthly_hours': monthly_hours,
            'pending_leaves': pending_leaves,
            'page_name': 'employee_dashboard',
            'has_leave_module': 'hr.leave' in request.env and request.env['hr.leave'].check_access('read'),
            'has_timesheet_module': 'account.analytic.line' in request.env,
            'has_payroll_module': 'hr.payslip' in request.env,
            'has_project_access': has_project_access,
        }

        return request.render("employee_portal_hub.employee_dashboard", values)

    @http.route(['/my/home'], type='http', auth="user", website=True)
    def redirect_to_dashboard(self, **kw):
        """Redirect /my/home to /my/dashboard"""
        return request.redirect('/my/dashboard')

    @http.route(['/my/employee/profile'], type='http', auth="user", website=True)
    def employee_profile(self, **kw):
        """Employee profile page"""
        if not request.env.user.employee_id:
            return request.render("employee_portal_hub.no_employee_error")

        employee = request.env.user.employee_id

        values = {
            'employee': employee,
            'page_name': 'employee_profile',
            'return_url': '/my/dashboard',
        }

        return request.render("employee_portal_hub.employee_profile", values)

    @http.route(['/my/timesheets', '/my/timesheets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timesheets(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """Timesheet portal page"""
        if not request.env.user.employee_id:
            return request.render("employee_portal_hub.no_employee_error")

        # Use user_id for filtering since account.analytic.line doesn't have employee_id field
        # unless hr_timesheet module is installed
        domain = [
            ('user_id', '=', request.env.user.id)
        ]

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'date desc'},
            'name': {'label': _('Description'), 'order': 'name'},
            'hours': {'label': _('Hours'), 'order': 'unit_amount desc'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date', '>=', date_begin), ('date', '<=', date_end)]

        timesheet_count = request.env['account.analytic.line'].search_count(domain)
        pager = portal_pager(
            url="/my/timesheets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=timesheet_count,
            page=page,
            step=self._items_per_page
        )

        timesheets = request.env['account.analytic.line'].search(
            domain, order=order, limit=self._items_per_page, offset=pager['offset']
        )

        values = {
            'timesheets': timesheets,
            'page_name': 'timesheets',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'date_begin': date_begin,
            'date_end': date_end,
            'default_url': '/my/timesheets',
        }

        return request.render("employee_portal_hub.portal_my_timesheets", values)

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_payslips(self, page=1, sortby=None, filterby=None, **kw):
        """Payslip portal page"""
        if not request.env.user.employee_id:
            return request.render("employee_portal_hub.no_employee_error")

        employee = request.env.user.employee_id
        domain = [('employee_id', '=', employee.id)]

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'date_from desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
            'paid': {'label': _('Paid'), 'domain': [('state', '=', 'paid')]},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        payslip_count = request.env['hr.payslip'].search_count(domain)
        pager = portal_pager(
            url="/my/payslips",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )

        payslips = request.env['hr.payslip'].search(
            domain, order=order, limit=self._items_per_page, offset=pager['offset']
        )

        values = {
            'payslips': payslips,
            'page_name': 'payslips',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
            'default_url': '/my/payslips',
        }

        return request.render("employee_portal_hub.portal_my_payslips", values)

    @http.route(['/my/payslips/<int:payslip_id>'], type='http', auth="user", website=True)
    def portal_payslip_detail(self, payslip_id, access_token=None, **kw):
        """Individual payslip detail page"""
        try:
            payslip_sudo = self._document_check_access('hr.payslip', payslip_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'payslip': payslip_sudo,
            'page_name': 'payslip_detail',
            'return_url': '/my/payslips',
        }

        return request.render("employee_portal_hub.portal_payslip_detail", values)

    @http.route(['/my/employee/leaves/calendar'], type='json', auth="user", website=True)
    def employee_leaves_calendar(self, start_date=None, end_date=None, **kw):
        """Return leave data for calendar display"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': _('No employee record found')}

        domain = [('employee_id', '=', employee.id)]

        # Filter by date range if provided
        if start_date and end_date:
            domain += [
                '|',
                '&', ('date_from', '>=', start_date), ('date_from', '<=', end_date),
                '|',
                '&', ('date_to', '>=', start_date), ('date_to', '<=', end_date),
                '&', ('date_from', '<=', start_date), ('date_to', '>=', end_date)
            ]

        leaves = request.env['hr.leave'].search_read(
            domain=domain,
            fields=['id', 'name', 'date_from', 'date_to', 'state', 'holiday_status_id'],
            order='date_from desc'
        )

        # Format data for calendar
        calendar_leaves = []
        for leave in leaves:
            calendar_leaves.append({
                'id': leave['id'],
                'name': leave['name'],
                'date_from': leave['date_from'],
                'date_to': leave['date_to'],
                'state': leave['state'],
                'leave_type_name': leave['holiday_status_id'][1]
            })

        return {
            'leaves': calendar_leaves
        }

    # Leave Request Management Routes
    def _get_leave_request_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
            'date_from': {'label': _('Start Date'), 'order': 'request_date_from desc'},
        }

    def _get_leave_request_searchbar_filters(self):
        return {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'confirm': {'label': _('Submitted'), 'domain': [('state', '=', 'confirm')]},
            'validate1': {'label': _('First Approval'), 'domain': [('state', '=', 'validate1')]},
            'validate': {'label': _('Approved'), 'domain': [('state', '=', 'validate')]},
            'refuse': {'label': _('Refused'), 'domain': [('state', '=', 'refuse')]},
        }

    @http.route(['/my/leave_requests', '/my/leave_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leave_requests(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """Display leave requests in portal"""
        values = self._prepare_portal_layout_values()
        HrLeave = request.env['hr.leave']

        # Check if user has employee record
        if not request.env.user.employee_id:
            return request.render("employee_portal_hub.no_employee_error")

        # Domain for current user's leave requests
        domain = [('employee_id.user_id', '=', request.env.user.id)]

        searchbar_sortings = self._get_leave_request_searchbar_sortings()
        searchbar_filters = self._get_leave_request_searchbar_filters()

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # dates
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # pager
        leave_request_count = HrLeave.search_count(domain)
        pager = portal_pager(
            url="/my/leave_requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=leave_request_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        leave_requests = HrLeave.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'leave_requests': leave_requests,
            'page_name': 'leave_requests',
            'default_url': '/my/leave_requests',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("employee_portal_hub.portal_my_leave_requests", values)

    @http.route(['/my/leave_requests/<int:leave_id>'], type='http', auth="user", website=True)
    def portal_leave_request_detail(self, leave_id, access_token=None, **kw):
        """Display a specific leave request"""
        try:
            leave_sudo = self._document_check_access('hr.leave', leave_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my/leave_requests')

        values = {
            'leave': leave_sudo,
            'page_name': 'leave_request_detail',
            'return_url': '/my/leave_requests',
        }
        return request.render("employee_portal_hub.portal_leave_request_detail", values)

    @http.route(['/my/leave_requests/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_leave_request_new(self, **kw):
        """Create new leave request"""
        if request.httprequest.method == 'POST':
            return self._create_leave_request(**kw)

        # GET request - show form
        employee = request.env.user.employee_id
        if not employee:
            return request.render("employee_portal_hub.no_employee_error")

        # Get available leave types
        leave_types = request.env['hr.leave.type'].search([('active', '=', True)])

        values = {
            'employee': employee,
            'leave_types': leave_types,
            'page_name': 'leave_request_new',
            'return_url': '/my/leave_requests',
        }
        return request.render("employee_portal_hub.portal_leave_request_new", values)

    def _create_leave_request(self, **kw):
        """Handle leave request creation from portal"""
        try:
            # Validate employee
            employee = request.env.user.employee_id
            if not employee:
                return request.render("employee_portal_hub.no_employee_error")

            # Prepare values for hr.leave model
            vals = {
                'employee_id': employee.id,
                'holiday_status_id': int(kw.get('holiday_status_id')),
                'request_date_from': kw.get('request_date_from'),
                'request_date_to': kw.get('request_date_to'),
                'name': kw.get('name') or '',
            }

            # Create leave request
            leave_request = request.env['hr.leave'].create(vals)

            # Handle file uploads
            if 'attachment' in request.httprequest.files:
                attachments = request.httprequest.files.getlist('attachment')
                for attachment in attachments:
                    if attachment.filename:
                        attachment_value = {
                            'name': attachment.filename,
                            'datas': attachment.read(),
                            'res_model': 'hr.leave',
                            'res_id': leave_request.id,
                        }
                        request.env['ir.attachment'].create(attachment_value)

            # Submit automatically if requested
            if kw.get('submit_immediately'):
                try:
                    leave_request.action_confirm()
                    message = _('Your leave request has been submitted successfully!')
                except (ValidationError, UserError) as e:
                    message = str(e)
            else:
                message = _('Your leave request has been saved as draft!')

            return request.redirect(f'/my/leave_requests/{leave_request.id}?message={message}')

        except (ValidationError, UserError) as e:
            _logger.warning(f"Validation error creating leave request: {e}")
            error_message = str(e)
            return request.render("employee_portal_hub.portal_leave_request_new", {
                'error': error_message,
                'employee': request.env.user.employee_id,
                'leave_types': request.env['hr.leave.type'].search([('active', '=', True)]),
                'values': kw,
            })
        except Exception as e:
            _logger.error(f"Error creating leave request: {e}")
            error_message = _('An error occurred while creating your leave request. Please try again.')
            return request.render("employee_portal_hub.portal_leave_request_new", {
                'error': error_message,
                'employee': request.env.user.employee_id,
                'leave_types': request.env['hr.leave.type'].search([('active', '=', True)]),
                'values': kw,
            })

    @http.route(['/my/leave_requests/<int:leave_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_leave_request_edit(self, leave_id, **kw):
        """Edit existing leave request (only if in draft state)"""
        try:
            leave = self._document_check_access('hr.leave', leave_id)
        except (AccessError, MissingError):
            return request.redirect('/my/leave_requests')

        if leave.state != 'draft':
            return request.redirect(f'/my/leave_requests/{leave_id}?message={_("Only draft requests can be edited.")}')

        if request.httprequest.method == 'POST':
            return self._update_leave_request(leave, **kw)

        # GET request - show edit form
        values = {
            'leave': leave,
            'leave_types': request.env['hr.leave.type'].search([('active', '=', True)]),
            'page_name': 'leave_request_edit',
            'return_url': f'/my/leave_requests/{leave_id}',
        }
        return request.render("employee_portal_hub.portal_leave_request_edit", values)

    def _update_leave_request(self, leave, **kw):
        """Handle leave request update from portal"""
        try:
            # Prepare values for hr.leave model
            vals = {
                'holiday_status_id': int(kw.get('holiday_status_id')),
                'request_date_from': kw.get('request_date_from'),
                'request_date_to': kw.get('request_date_to'),
                'name': kw.get('name') or '',
            }

            # Update leave request
            leave.write(vals)

            # Handle file uploads
            if 'attachment' in request.httprequest.files:
                attachments = request.httprequest.files.getlist('attachment')
                for attachment in attachments:
                    if attachment.filename:
                        attachment_value = {
                            'name': attachment.filename,
                            'datas': attachment.read(),
                            'res_model': 'hr.leave',
                            'res_id': leave.id,
                        }
                        request.env['ir.attachment'].create(attachment_value)

            # Submit automatically if requested
            if kw.get('submit_immediately'):
                try:
                    leave.action_confirm()
                    message = _('Your leave request has been updated and submitted successfully!')
                except (ValidationError, UserError) as e:
                    message = str(e)
            else:
                message = _('Your leave request has been updated successfully!')

            return request.redirect(f'/my/leave_requests/{leave.id}?message={message}')

        except (ValidationError, UserError) as e:
            _logger.warning(f"Validation error updating leave request: {e}")
            error_message = str(e)
            return request.render("employee_portal_hub.portal_leave_request_edit", {
                'error': error_message,
                'leave': leave,
                'leave_types': request.env['hr.leave.type'].search([('active', '=', True)]),
                'values': kw,
            })
        except Exception as e:
            _logger.error(f"Error updating leave request: {e}")
            error_message = _('An error occurred while updating your leave request. Please try again.')
            return request.render("employee_portal_hub.portal_leave_request_edit", {
                'error': error_message,
                'leave': leave,
                'leave_types': request.env['hr.leave.type'].search([('active', '=', True)]),
                'values': kw,
            })

    @http.route(['/my/leave_requests/<int:leave_id>/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_leave_request_submit(self, leave_id, **kw):
        """Submit leave request for approval"""
        try:
            leave = self._document_check_access('hr.leave', leave_id)
            leave.action_confirm()
            message = _('Your leave request has been submitted for approval!')
        except (AccessError, MissingError):
            message = _('Access denied or leave request not found.')
        except (ValidationError, UserError) as e:
            message = str(e)
        except Exception as e:
            _logger.error(f"Error submitting leave request: {e}")
            message = _('An error occurred while submitting your leave request.')

        return request.redirect(f'/my/leave_requests/{leave_id}?message={message}')

    @http.route(['/my/leave_requests/<int:leave_id>/cancel'], type='http', auth="user", website=True, methods=['POST'])
    def portal_leave_request_cancel(self, leave_id, **kw):
        """Cancel leave request"""
        try:
            leave = self._document_check_access('hr.leave', leave_id)
            if leave.state in ['validate', 'refuse']:
                raise UserError(_('Cannot cancel approved or refused requests.'))
            leave.action_draft()
            message = _('Your leave request has been cancelled.')
        except (AccessError, MissingError):
            message = _('Access denied or leave request not found.')
        except Exception as e:
            _logger.error(f"Error cancelling leave request: {e}")
            message = _('An error occurred while cancelling your leave request.')

        return request.redirect(f'/my/leave_requests/{leave_id}?message={message}')
