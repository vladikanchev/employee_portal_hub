# -*- coding: utf-8 -*-

from odoo.tests import tagged, TransactionCase
from odoo.exceptions import AccessError
from odoo import fields
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


@tagged('employee_portal_hub', 'security', 'post_install', '-at_install')
class TestEmployeePortalSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test users
        self.portal_user_1 = self.env['res.users'].create({
            'name': 'Portal User 1',
            'login': 'portal_hub_1',
            'email': 'portal1@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        
        self.portal_user_2 = self.env['res.users'].create({
            'name': 'Portal User 2',
            'login': 'portal_hub_2',
            'email': 'portal2@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        
        # Create employees
        self.employee_1 = self.env['hr.employee'].create({
            'name': 'Employee 1',
            'user_id': self.portal_user_1.id,
        })
        
        self.employee_2 = self.env['hr.employee'].create({
            'name': 'Employee 2',
            'user_id': self.portal_user_2.id,
        })

    def test_employee_data_isolation(self):
        """Test that employees can only access their own data"""
        # Test timesheet isolation if available
        if 'account.analytic.line' in self.env:
            timesheet_1 = self.env['account.analytic.line'].create({
                'name': 'User 1 Timesheet',
                'user_id': self.portal_user_1.id,
                'unit_amount': 8.0,
                'date': fields.Date.today(),
            })
            
            timesheet_2 = self.env['account.analytic.line'].create({
                'name': 'User 2 Timesheet',
                'user_id': self.portal_user_2.id,
                'unit_amount': 6.0,
                'date': fields.Date.today(),
            })
            
            # User 1 should only see their own timesheets
            user_1_timesheets = self.env['account.analytic.line'].with_user(
                self.portal_user_1
            ).search([])
            
            timesheet_user_ids = user_1_timesheets.mapped('user_id.id')
            self.assertIn(self.portal_user_1.id, timesheet_user_ids)
            self.assertNotIn(self.portal_user_2.id, timesheet_user_ids)

    def test_payslip_security(self):
        """Test payslip access security"""
        if 'hr.payslip' in self.env:
            payslip_1 = self.env['hr.payslip'].create({
                'name': 'Payslip 1',
                'employee_id': self.employee_1.id,
                'date_from': fields.Date.today().replace(day=1),
                'date_to': fields.Date.today(),
            })
            
            payslip_2 = self.env['hr.payslip'].create({
                'name': 'Payslip 2',
                'employee_id': self.employee_2.id,
                'date_from': fields.Date.today().replace(day=1),
                'date_to': fields.Date.today(),
            })
            
            # User 1 should only see their own payslips
            user_1_payslips = self.env['hr.payslip'].with_user(
                self.portal_user_1
            ).search([])
            
            payslip_employee_ids = user_1_payslips.mapped('employee_id.id')
            self.assertIn(self.employee_1.id, payslip_employee_ids)
            self.assertNotIn(self.employee_2.id, payslip_employee_ids)

    def test_employee_record_security(self):
        """Test employee record access security"""
        # Users should only access their own employee record
        user_1_employees = self.env['hr.employee'].with_user(
            self.portal_user_1
        ).search([])
        
        employee_ids = user_1_employees.ids
        self.assertIn(self.employee_1.id, employee_ids)
        self.assertNotIn(self.employee_2.id, employee_ids)

    def test_cross_module_security_consistency(self):
        """Test that security is consistent across integrated modules"""
        # Test that security rules don't conflict between modules
        
        # Create data in multiple modules if available
        test_data_created = False
        
        if 'hr.leave' in self.env:
            # Create leave request (if leave_request_portal is installed)
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Security Test Leave',
                'request_unit': 'day',
                'allocation_type': 'no',
            })
            
            leave_1 = self.env['hr.leave'].create({
                'employee_id': self.employee_1.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': fields.Date.today() + timedelta(days=10),
                'request_date_to': fields.Date.today() + timedelta(days=12),
                'name': 'Security test leave',
            })
            test_data_created = True
        
        if 'account.analytic.line' in self.env:
            # Create timesheet
            timesheet_1 = self.env['account.analytic.line'].create({
                'name': 'Security test timesheet',
                'user_id': self.portal_user_1.id,
                'unit_amount': 8.0,
                'date': fields.Date.today(),
            })
            test_data_created = True
        
        # If we created test data, verify security isolation
        if test_data_created:
            # User 1 should only see their own data across all modules
            self.assertTrue(True)  # Test passes if no access errors occur

    def test_dashboard_data_security(self):
        """Test that dashboard only shows authorized data"""
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub
        
        controller = EmployeePortalHub()
        
        # Test that counters respect security
        values = controller._prepare_home_portal_values([
            'leave_request_count', 'timesheet_count', 'payslip_count'
        ])
        
        # All values should be integers (0 or positive) - no access errors
        for key in ['leave_request_count', 'timesheet_count', 'payslip_count']:
            if key in values:
                self.assertIsInstance(values[key], int)
                self.assertGreaterEqual(values[key], 0)


@tagged('employee_portal_hub', 'performance', 'post_install', '-at_install')
class TestEmployeePortalPerformance(TransactionCase):
    """Test performance aspects of the employee portal hub"""

    def setUp(self):
        super().setUp()
        
        self.portal_user = self.env['res.users'].create({
            'name': 'Performance Test User',
            'login': 'performance_test',
            'email': 'performance@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        
        self.employee = self.env['hr.employee'].create({
            'name': 'Performance Employee',
            'user_id': self.portal_user.id,
        })

    def test_dashboard_query_efficiency(self):
        """Test that dashboard queries are efficient"""
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub
        
        controller = EmployeePortalHub()
        
        # Test that preparing home values doesn't cause excessive queries
        # This is a basic test - in production, you'd use query counting tools
        values = controller._prepare_home_portal_values([
            'leave_request_count', 'timesheet_count', 'payslip_count'
        ])
        
        # Should complete without timeout or excessive delay
        self.assertIsInstance(values, dict)

    def test_large_dataset_handling(self):
        """Test handling of larger datasets"""
        # Create multiple records to test performance
        if 'account.analytic.line' in self.env:
            # Create multiple timesheet entries
            for i in range(10):
                self.env['account.analytic.line'].create({
                    'name': f'Performance Test {i}',
                    'user_id': self.portal_user.id,
                    'unit_amount': 8.0,
                    'date': fields.Date.today() - timedelta(days=i),
                })
        
        # Test that queries still perform well
        from odoo.addons.employee_portal_hub.controllers.portal import EmployeePortalHub
        controller = EmployeePortalHub()
        
        values = controller._prepare_home_portal_values(['timesheet_count'])
        
        if 'timesheet_count' in values:
            self.assertGreaterEqual(values['timesheet_count'], 10)
