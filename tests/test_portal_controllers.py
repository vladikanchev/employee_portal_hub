# -*- coding: utf-8 -*-

from odoo.tests.common import HttpCase
from odoo.tests import tagged
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestPortalControllers(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test user and employee
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Portal User',
            'login': 'test_portal_user',
            'email': 'test_portal_user@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('employee_portal_hub.group_employee_portal_user').id
            ])]
        })
        
        cls.test_employee = cls.env['hr.employee'].create({
            'name': 'Test Portal User',
            'work_email': 'test_portal_user@example.com',
            'user_id': cls.test_user.id,
            'portal_access_enabled': True,
        })

    def test_employee_dashboard_access(self):
        """Test employee dashboard is accessible"""
        self.authenticate('test_portal_user', 'test_portal_user')
        
        response = self.url_open('/my/employee')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.content)

    def test_employee_profile_access(self):
        """Test employee profile page is accessible"""
        self.authenticate('test_portal_user', 'test_portal_user')
        
        response = self.url_open('/my/employee/profile')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Profile', response.content)

    def test_dashboard_without_employee_record(self):
        """Test dashboard redirects when user has no employee record"""
        # Create user without employee
        user_no_employee = self.env['res.users'].create({
            'name': 'User No Employee',
            'login': 'user_no_employee',
            'email': 'noemployee@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        self.authenticate('user_no_employee', 'user_no_employee')
        
        response = self.url_open('/my/employee')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No Employee Record Found', response.content)

    def test_timesheet_portal_conditional(self):
        """Test timesheet portal only shows when module is available"""
        self.authenticate('test_portal_user', 'test_portal_user')
        
        # Mock the module availability check
        with patch.object(self.env.registry, '__contains__', side_effect=lambda x: x != 'account.analytic.line'):
            response = self.url_open('/my/employee')
            self.assertEqual(response.status_code, 200)
            # Should not contain timesheet links when module not available
            self.assertNotIn(b'/my/timesheets', response.content)

    def test_payslip_portal_conditional(self):
        """Test payslip portal only shows when module is available"""
        self.authenticate('test_portal_user', 'test_portal_user')
        
        # Mock the module availability check
        with patch.object(self.env.registry, '__contains__', side_effect=lambda x: x != 'hr.payslip'):
            response = self.url_open('/my/employee')
            self.assertEqual(response.status_code, 200)
            # Should not contain payslip links when module not available
            self.assertNotIn(b'/my/payslips', response.content)

    def test_portal_home_integration(self):
        """Test that employee portal appears in portal home"""
        self.authenticate('test_portal_user', 'test_portal_user')
        
        response = self.url_open('/my')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Employee Dashboard', response.content)

    def test_dashboard_stats_calculation(self):
        """Test dashboard statistics are calculated correctly"""
        self.authenticate('test_portal_user', 'test_portal_user')
        
        # Create some test data if modules are available
        if 'account.analytic.line' in self.env:
            # Create test project and timesheet
            project = self.env['project.project'].create({
                'name': 'Test Project'
            })
            
            self.env['account.analytic.line'].create({
                'name': 'Test Timesheet Entry',
                'employee_id': self.test_employee.id,
                'project_id': project.id,
                'unit_amount': 8.0,
                'date': '2025-07-02',
            })
        
        response = self.url_open('/my/employee')
        self.assertEqual(response.status_code, 200)
        # Should contain dashboard statistics
        self.assertIn(b'Hours This Month', response.content)

    def test_security_employee_access_only(self):
        """Test that employees can only access their own data"""
        # Create another employee
        other_user = self.env['res.users'].create({
            'name': 'Other Employee',
            'login': 'other_employee',
            'email': 'other@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        other_employee = self.env['hr.employee'].create({
            'name': 'Other Employee',
            'work_email': 'other@example.com',
            'user_id': other_user.id,
        })
        
        # Create document for other employee
        test_attachment = self.env['ir.attachment'].create({
            'name': 'Other Document.pdf',
            'type': 'binary',
            'datas': b'Other content',
            'mimetype': 'application/pdf',
        })
        
        other_document = self.env['employee.document'].create({
            'document_name': 'Other Employee Document',
            'employee_id': other_employee.id,
            'document_type': 'contract',
            'attachment_id': test_attachment.id,
        })
        
        # Login as test user and try to access other's documents
        self.authenticate('test_portal_user', 'test_portal_user')
        
        # Should not be able to see other employee's documents
        with self.assertRaises(Exception):
            self.env['employee.document'].with_user(self.test_user).browse(other_document.id).read()

    def test_welcome_email_template(self):
        """Test that welcome email template exists and is valid"""
        template = self.env.ref('employee_portal_hub.employee_portal_welcome_template')
        
        self.assertTrue(template)
        self.assertEqual(template.model_id.model, 'hr.employee')
        self.assertIn('Welcome to Employee Portal', template.subject)
        self.assertIn('{{ object.name }}', template.subject)
        
        # Test email generation
        mail_values = template.generate_email(self.test_employee.id)
        self.assertIn('Test Portal User', mail_values['subject'])
        self.assertIn('Test Portal User', mail_values['body_html'])
