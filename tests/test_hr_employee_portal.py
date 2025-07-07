# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestHrEmployeePortal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test user and employee
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Portal Employee',
            'login': 'test_portal_employee',
            'email': 'test_portal@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.test_employee = cls.env['hr.employee'].create({
            'name': 'Test Portal Employee',
            'work_email': 'test_portal@example.com',
            'user_id': cls.test_user.id,
        })

    def test_hr_employee_portal_fields(self):
        """Test that HR employee has portal-related fields"""
        employee = self.test_employee
        
        # Test default values
        self.assertFalse(employee.portal_access_enabled)
        self.assertTrue(employee.portal_notification_email)
        self.assertFalse(employee.last_portal_login)

    def test_enable_portal_access(self):
        """Test enabling portal access for employee"""
        employee = self.test_employee
        
        # Enable portal access
        employee.action_enable_portal_access()
        
        self.assertTrue(employee.portal_access_enabled)
        
        # Check that user has portal group
        portal_group = self.env.ref('employee_portal_hub.group_employee_portal_user')
        self.assertIn(portal_group, employee.user_id.groups_id)

    def test_disable_portal_access(self):
        """Test disabling portal access for employee"""
        employee = self.test_employee
        
        # First enable it
        employee.action_enable_portal_access()
        self.assertTrue(employee.portal_access_enabled)
        
        # Then disable it
        employee.action_disable_portal_access()
        self.assertFalse(employee.portal_access_enabled)
        
        # Check that user no longer has portal group
        portal_group = self.env.ref('employee_portal_hub.group_employee_portal_user')
        self.assertNotIn(portal_group, employee.user_id.groups_id)

    def test_update_last_login(self):
        """Test updating last portal login"""
        # Switch to test user context
        with self.env(user=self.test_user):
            result = self.env['hr.employee'].update_last_login()
            self.assertTrue(result)
            
            # Check that last login was updated
            self.test_employee.refresh()
            self.assertTrue(self.test_employee.last_portal_login)

    def test_employee_document_relationship(self):
        """Test employee document relationship"""
        employee = self.test_employee
        
        # Create test attachment
        test_attachment = self.env['ir.attachment'].create({
            'name': 'Test Document.pdf',
            'type': 'binary',
            'datas': b'Test content',
            'mimetype': 'application/pdf',
        })
        
        # Create employee document
        document = self.env['employee.document'].create({
            'document_name': 'Test Employee Document',
            'employee_id': employee.id,
            'document_type': 'contract',
            'attachment_id': test_attachment.id,
        })
        
        # Test relationship
        self.assertIn(document, employee.employee_document_ids)
        self.assertEqual(document.employee_id, employee)

    def test_portal_access_without_user(self):
        """Test that portal access methods handle employees without users"""
        # Create employee without user
        employee_no_user = self.env['hr.employee'].create({
            'name': 'Employee No User',
            'work_email': 'nouser@example.com',
        })
        
        # Trying to enable portal access should not crash
        employee_no_user.action_enable_portal_access()
        # Should remain False since no user exists
        self.assertFalse(employee_no_user.portal_access_enabled)

    def test_employee_portal_view_inheritance(self):
        """Test that employee form view includes portal fields"""
        # Get the inherited view
        view = self.env.ref('employee_portal_hub.hr_employee_portal_form_view')
        
        self.assertTrue(view)
        self.assertEqual(view.model, 'hr.employee')
        self.assertEqual(view.inherit_id.model, 'hr.employee')
        
        # Check that view includes portal fields in arch
        arch_string = str(view.arch)
        self.assertIn('portal_access_enabled', arch_string)
        self.assertIn('portal_notification_email', arch_string)
        self.assertIn('last_portal_login', arch_string)
