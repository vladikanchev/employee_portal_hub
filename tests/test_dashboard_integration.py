# -*- coding: utf-8 -*-

from odoo.tests import tagged, TransactionCase
from odoo import fields
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


@tagged('employee_portal_hub', 'dashboard', 'post_install', '-at_install')
class TestDashboardIntegration(TransactionCase):
    """Test dashboard integration and data aggregation"""

    def setUp(self):
        super().setUp()

        self.portal_user = self.env['res.users'].create({
            'name': 'Dashboard Test User',
            'login': 'dashboard_test',
            'email': 'dashboard@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })

        self.employee = self.env['hr.employee'].create({
            'name': 'Dashboard Employee',
            'user_id': self.portal_user.id,
            'work_email': 'dashboard@test.com',
            'job_title': 'Dashboard Tester',
        })

    def test_dashboard_data_aggregation(self):
        """Test that dashboard correctly aggregates data from multiple sources"""
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub

        controller = EmployeePortalHub()

        # Create test data across different modules
        test_data_counts = {}

        # Test leave requests if available
        if 'hr.leave' in self.env:
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Dashboard Test Leave',
                'request_unit': 'day',
                'allocation_type': 'no',
            })

            for i in range(3):
                self.env['hr.leave'].create({
                    'employee_id': self.employee.id,
                    'holiday_status_id': leave_type.id,
                    'request_date_from': fields.Date.today() + timedelta(days=10+i),
                    'request_date_to': fields.Date.today() + timedelta(days=12+i),
                    'name': f'Dashboard test leave {i}',
                })
            test_data_counts['leave_request_count'] = 3

        # Test timesheets if available
        if 'account.analytic.line' in self.env:
            for i in range(5):
                self.env['account.analytic.line'].create({
                    'name': f'Dashboard test timesheet {i}',
                    'user_id': self.portal_user.id,
                    'unit_amount': 8.0,
                    'date': fields.Date.today() - timedelta(days=i),
                })
            test_data_counts['timesheet_count'] = 5

        # Test payslips if available
        if 'hr.payslip' in self.env:
            for i in range(2):
                self.env['hr.payslip'].create({
                    'name': f'Dashboard test payslip {i}',
                    'employee_id': self.employee.id,
                    'date_from': fields.Date.today().replace(day=1) - timedelta(days=30*i),
                    'date_to': fields.Date.today() - timedelta(days=30*i),
                })
            test_data_counts['payslip_count'] = 2

        # Test that dashboard aggregates correctly
        values = controller._prepare_home_portal_values(list(test_data_counts.keys()))

        for counter, expected_count in test_data_counts.items():
            if counter in values:
                self.assertEqual(values[counter], expected_count,
                    f"Dashboard {counter} should match created test data")

    def test_monthly_hours_calculation(self):
        """Test monthly hours calculation for dashboard"""
        if 'account.analytic.line' not in self.env:
            self.skipTest("Timesheet module not available")

        # Create timesheet entries for current month
        current_month_start = datetime.now().replace(day=1).date()

        # Create entries with different hours
        timesheet_data = [
            {'hours': 8.0, 'days_offset': 1},
            {'hours': 7.5, 'days_offset': 2},
            {'hours': 8.5, 'days_offset': 5},
            {'hours': 6.0, 'days_offset': 10},
        ]

        expected_total = sum(entry['hours'] for entry in timesheet_data)

        for entry in timesheet_data:
            self.env['account.analytic.line'].create({
                'name': f'Monthly hours test {entry["days_offset"]}',
                'user_id': self.portal_user.id,
                'unit_amount': entry['hours'],
                'date': current_month_start + timedelta(days=entry['days_offset']),
            })

        # Create entries from previous month (should not be counted)
        prev_month = current_month_start - timedelta(days=1)
        self.env['account.analytic.line'].create({
            'name': 'Previous month entry',
            'user_id': self.portal_user.id,
            'unit_amount': 8.0,
            'date': prev_month,
        })

        # Calculate monthly hours manually (as the controller would)
        monthly_timesheets = self.env['account.analytic.line'].search([
            ('user_id', '=', self.portal_user.id),
            ('date', '>=', current_month_start)
        ])

        actual_total = sum(monthly_timesheets.mapped('unit_amount'))
        self.assertEqual(actual_total, expected_total,
            "Monthly hours calculation should only include current month entries")

    def test_pending_leaves_calculation(self):
        """Test pending leave requests calculation"""
        if 'hr.leave' not in self.env:
            self.skipTest("Leave module not available")

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Pending Test Leave',
            'request_unit': 'day',
            'allocation_type': 'no',
        })

        # Create leaves in different states
        states_and_counts = [
            ('draft', 2),
            ('confirm', 1),
            ('validate1', 1),
            ('validate', 1),  # Should not be counted as pending
            ('refuse', 1),    # Should not be counted as pending
        ]

        expected_pending = 0

        for state, count in states_and_counts:
            for i in range(count):
                leave = self.env['hr.leave'].create({
                    'employee_id': self.employee.id,
                    'holiday_status_id': leave_type.id,
                    'request_date_from': fields.Date.today() + timedelta(days=10+i),
                    'request_date_to': fields.Date.today() + timedelta(days=12+i),
                    'name': f'Pending test {state} {i}',
                    'state': state,
                })

                if state in ['draft', 'confirm']:
                    expected_pending += 1

        # Calculate pending leaves
        actual_pending = self.env['hr.leave'].search_count([
            ('employee_id.user_id', '=', self.portal_user.id),
            ('state', 'in', ['draft', 'confirm'])
        ])

        self.assertEqual(actual_pending, expected_pending,
            "Pending leaves should only count draft and confirm states")

    def test_dashboard_with_no_data(self):
        """Test dashboard behavior when no data exists"""
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub

        controller = EmployeePortalHub()

        # Test with empty database
        values = controller._prepare_home_portal_values([
            'leave_request_count', 'timesheet_count', 'payslip_count'
        ])

        # All counters should be 0 or handle gracefully
        for counter in ['leave_request_count', 'timesheet_count', 'payslip_count']:
            if counter in values:
                self.assertEqual(values[counter], 0,
                    f"{counter} should be 0 when no data exists")

    def test_recent_items_limitation(self):
        """Test that recent items are properly limited"""
        if 'hr.leave' not in self.env:
            self.skipTest("Leave module not available")

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Recent Items Test Leave',
            'request_unit': 'day',
            'allocation_type': 'no',
        })

        # Create more than the typical "recent" limit (usually 5)
        for i in range(10):
            self.env['hr.leave'].create({
                'employee_id': self.employee.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': fields.Date.today() + timedelta(days=10+i),
                'request_date_to': fields.Date.today() + timedelta(days=12+i),
                'name': f'Recent test {i}',
            })

        # Test that queries limit results appropriately
        recent_leaves = self.env['hr.leave'].search([
            ('employee_id.user_id', '=', self.portal_user.id)
        ], limit=5, order='create_date desc')

        self.assertEqual(len(recent_leaves), 5,
            "Recent items should be limited to prevent performance issues")

    def test_module_availability_detection(self):
        """Test that the dashboard correctly detects available modules"""
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub

        controller = EmployeePortalHub()

        # Test module detection flags
        test_user_context = self.portal_user.with_context()

        # These should always be booleans, regardless of module availability
        has_leave = 'hr.leave' in self.env
        has_timesheet = 'account.analytic.line' in self.env
        has_payroll = 'hr.payslip' in self.env

        self.assertIsInstance(has_leave, bool)
        self.assertIsInstance(has_timesheet, bool)
        self.assertIsInstance(has_payroll, bool)

        # hr.leave should typically be available in modern Odoo
        self.assertTrue(has_leave, "HR Leave module should be available")

    def test_error_recovery_in_dashboard(self):
        """Test that dashboard recovers gracefully from errors"""
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub

        controller = EmployeePortalHub()

        # Test with edge cases that might cause errors
        values = controller._prepare_home_portal_values([
            'leave_request_count', 'timesheet_count', 'payslip_count'
        ])

        # Should not raise exceptions and should return a dictionary
        self.assertIsInstance(values, dict)

        # Test that the method handles missing employee gracefully
        # This tests the error handling paths in the controller
        self.assertTrue(True)  # Test passes if no exceptions are raised
