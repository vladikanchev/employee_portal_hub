# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Portal Access Fields
    portal_access_enabled = fields.Boolean(
        string='Portal Access Enabled',
        default=False,
        help="Enable portal access for this employee"
    )

    portal_notification_email = fields.Boolean(
        string='Receive Portal Notifications',
        default=True,
        help="Receive email notifications for portal activities"
    )

    last_portal_login = fields.Datetime(
        string='Last Portal Login',
        readonly=True,
        help="Last time the employee logged into the portal"
    )

    @api.model
    def update_last_login(self):
        """Update last portal login timestamp"""
        if self.env.user.employee_id:
            self.env.user.employee_id.write({
                'last_portal_login': fields.Datetime.now()
            })
            return True
        return False

    def action_enable_portal_access(self):
        """Enable portal access for employee"""
        for employee in self:
            if not employee.work_email:
                raise UserError(_("Employee must have a work email to enable portal access."))

            if not employee.user_id:
                # Create a new portal user for the employee
                user_vals = {
                    'name': employee.name,
                    'login': employee.work_email,
                    'email': employee.work_email,
                    'employee_ids': [(4, employee.id)],
                    'groups_id': [(6, 0, [
                        self.env.ref('base.group_portal').id,
                        self.env.ref('employee_portal_hub.group_employee_portal_user').id
                    ])]
                }
                user = self.env['res.users'].create(user_vals)
                employee.user_id = user
            else:
                # Add portal groups to existing user
                portal_group = self.env.ref('base.group_portal')
                employee_portal_group = self.env.ref('employee_portal_hub.group_employee_portal_user')

                groups_to_add = []
                if portal_group not in employee.user_id.groups_id:
                    groups_to_add.append(portal_group.id)
                if employee_portal_group not in employee.user_id.groups_id:
                    groups_to_add.append(employee_portal_group.id)

                if groups_to_add:
                    employee.user_id.write({
                        'groups_id': [(4, group_id) for group_id in groups_to_add]
                    })

            employee.write({
                'portal_access_enabled': True
            })

            # Send welcome email
            template = self.env.ref('employee_portal_hub.employee_portal_welcome_template', raise_if_not_found=False)
            if template:
                template.send_mail(employee.id, force_send=True)

    def action_disable_portal_access(self):
        """Disable portal access for employee"""
        for employee in self:
            if not employee.user_id:
                continue

            # Remove portal groups from user
            portal_group = self.env.ref('base.group_portal')
            employee_portal_group = self.env.ref('employee_portal_hub.group_employee_portal_user')

            groups_to_remove = []
            if portal_group in employee.user_id.groups_id:
                groups_to_remove.append(portal_group.id)
            if employee_portal_group in employee.user_id.groups_id:
                groups_to_remove.append(employee_portal_group.id)

            if groups_to_remove:
                employee.user_id.write({
                    'groups_id': [(3, group_id) for group_id in groups_to_remove]
                })

            employee.write({
                'portal_access_enabled': False
            })

    def action_open_portal_dashboard(self):
        """Open employee portal dashboard"""
        self.ensure_one()
        if not self.portal_access_enabled or not self.user_id:
            raise UserError(_("Portal access is not enabled for this employee."))

        return {
            'type': 'ir.actions.act_url',
            'url': '/my/dashboard',
            'target': 'new',
        }

    def action_send_portal_invitation(self):
        """Send portal invitation email"""
        self.ensure_one()
        if not self.portal_access_enabled or not self.user_id:
            raise UserError(_("Portal access is not enabled for this employee."))

        template = self.env.ref('employee_portal_hub.employee_portal_welcome_template', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Portal Invitation Sent'),
                    'message': _('Portal invitation has been sent to %s') % self.work_email,
                    'type': 'success',
                }
            }
        else:
            raise UserError(_("Portal invitation email template not found."))
