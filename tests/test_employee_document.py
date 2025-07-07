# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestEmployeeDocument(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test user and employee
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Employee User',
            'login': 'test_employee',
            'email': 'test_employee@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.test_employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_email': 'test_employee@example.com',
            'user_id': cls.test_user.id,
        })
        
        # Create test attachment
        cls.test_attachment = cls.env['ir.attachment'].create({
            'name': 'Test Document.pdf',
            'type': 'binary',
            'datas': b'Test content',
            'mimetype': 'application/pdf',
        })

    def test_employee_document_creation(self):
        """Test creating an employee document"""
        document = self.env['employee.document'].create({
            'document_name': 'Test Contract',
            'employee_id': self.test_employee.id,
            'document_type': 'contract',
            'attachment_id': self.test_attachment.id,
            'description': 'Test contract document',
            'is_confidential': True,
            'is_mandatory_read': True,
        })
        
        self.assertEqual(document.document_name, 'Test Contract')
        self.assertEqual(document.employee_id, self.test_employee)
        self.assertEqual(document.document_type, 'contract')
        self.assertTrue(document.is_confidential)
        self.assertTrue(document.is_mandatory_read)
        self.assertFalse(document.read_date)

    def test_document_mark_as_read(self):
        """Test marking document as read"""
        document = self.env['employee.document'].create({
            'document_name': 'Test Policy',
            'employee_id': self.test_employee.id,
            'document_type': 'policy',
            'attachment_id': self.test_attachment.id,
            'is_mandatory_read': True,
        })
        
        # Mark as read
        document.mark_as_read()
        
        self.assertTrue(document.read_date)
        self.assertLessEqual(
            (datetime.now() - document.read_date).total_seconds(), 
            5  # Should be within 5 seconds
        )

    def test_document_download_action(self):
        """Test document download action"""
        document = self.env['employee.document'].create({
            'document_name': 'Test Download',
            'employee_id': self.test_employee.id,
            'document_type': 'other',
            'attachment_id': self.test_attachment.id,
        })
        
        action = document.download_document()
        
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn(str(self.test_attachment.id), action['url'])
        self.assertEqual(action['target'], 'self')

    def test_document_download_no_attachment(self):
        """Test download action fails without attachment"""
        document = self.env['employee.document'].create({
            'document_name': 'Test No Attachment',
            'employee_id': self.test_employee.id,
            'document_type': 'other',
            'attachment_id': self.test_attachment.id,
        })
        
        # Remove attachment
        document.attachment_id = False
        
        with self.assertRaises(ValidationError):
            document.download_document()

    def test_document_expiry_filtering(self):
        """Test document expiry date filtering"""
        # Create expired document
        expired_doc = self.env['employee.document'].create({
            'document_name': 'Expired Document',
            'employee_id': self.test_employee.id,
            'document_type': 'certificate',
            'attachment_id': self.test_attachment.id,
            'expiry_date': datetime.now().date() - timedelta(days=10),
        })
        
        # Create future expiry document
        future_doc = self.env['employee.document'].create({
            'document_name': 'Future Document',
            'employee_id': self.test_employee.id,
            'document_type': 'certificate',
            'attachment_id': self.test_attachment.id,
            'expiry_date': datetime.now().date() + timedelta(days=10),
        })
        
        # Test that both documents exist
        all_docs = self.env['employee.document'].search([
            ('employee_id', '=', self.test_employee.id)
        ])
        self.assertIn(expired_doc, all_docs)
        self.assertIn(future_doc, all_docs)

    def test_document_categorization(self):
        """Test document category functionality"""
        categories = ['personal', 'company', 'hr', 'training']
        
        for category in categories:
            document = self.env['employee.document'].create({
                'document_name': f'Test {category.title()} Document',
                'employee_id': self.test_employee.id,
                'document_type': 'other',
                'attachment_id': self.test_attachment.id,
                'document_category': category,
            })
            self.assertEqual(document.document_category, category)

    def test_document_inheritance_mail_thread(self):
        """Test that document properly inherits mail.thread functionality"""
        document = self.env['employee.document'].create({
            'document_name': 'Test Mail Thread',
            'employee_id': self.test_employee.id,
            'document_type': 'other',
            'attachment_id': self.test_attachment.id,
        })
        
        # Test that mail.thread fields exist
        self.assertTrue(hasattr(document, 'message_ids'))
        self.assertTrue(hasattr(document, 'message_follower_ids'))
        
        # Test posting a message
        document.message_post(
            body="Test message",
            message_type='comment'
        )
        
        self.assertTrue(document.message_ids)
        self.assertEqual(document.message_ids[0].body, "<p>Test message</p>")
