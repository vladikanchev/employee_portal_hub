# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta
import json


class EmployeeDashboard(http.Controller):

    @http.route(['/my/employee/dashboard/stats'], type='json', auth="user", methods=['POST'])
    def get_dashboard_stats(self, **kw):
        """AJAX endpoint for dashboard statistics"""
        if not request.env.user.employee_id:
            return {'error': 'No employee record found'}
        
        employee = request.env.user.employee_id
        
        # Current month timesheet hours
        current_month = datetime.now().replace(day=1)
        monthly_hours = sum(request.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('date', '>=', current_month),
            ('project_id', '!=', False)
        ]).mapped('unit_amount'))
        
        # Leave balance (if available)
        leave_balance = 0
        if hasattr(employee, 'remaining_leaves'):
            leave_balance = employee.remaining_leaves
        
        # Pending approvals
        pending_leaves = request.env['leave.request.portal'].search_count([
            ('user_id', '=', request.env.user.id),
            ('state', 'in', ['draft', 'submitted'])
        ])
        
        # Recent activity count
        recent_activity = len(request.env['mail.message'].search([
            ('author_id', '=', request.env.user.partner_id.id)
        ], limit=10))
        
        return {
            'monthly_hours': monthly_hours,
            'leave_balance': leave_balance,
            'pending_leaves': pending_leaves,
            'recent_activity': recent_activity,
        }

    @http.route(['/my/employee/quick_action'], type='http', auth="user", website=True, methods=['POST'])
    def employee_quick_action(self, action_type=None, **kw):
        """Handle quick actions from dashboard"""
        if not request.env.user.employee_id:
            return request.redirect('/my')
        
        if action_type == 'new_leave':
            return request.redirect('/my/leave_requests/new')
        elif action_type == 'view_payslips':
            return request.redirect('/my/payslips')
        elif action_type == 'view_timesheets':
            return request.redirect('/my/timesheets')
        
        return request.redirect('/my/employee')
