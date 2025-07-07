{
    'name': 'Employee Portal Hub',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Comprehensive Employee Portal for HR Services',
    'description': """
        Employee Portal Hub
        ===================
        
        A comprehensive portal solution for employees providing:
        * Centralized dashboard with HR information
        * Leave request management using standard hr_holidays
        * Timesheet viewing and management
        * Payslip access and download
        * Employee profile and documents
        * Company announcements and policies
        * Mobile-responsive design
        
        Features:
        * Professional dashboard with key metrics
        * Direct integration with Odoo's standard hr_holidays module
        * Portal controllers for leave request submission
        * Payroll integration for payslip access
        * Document management for HR documents
        * Notification system for important updates
        * Enterprise-ready architecture for future scalability
        
        This module provides a professional employee self-service portal
        using standard Odoo modules without custom dependencies.
    """,
    'author': 'GoRoSoft',
    'website': 'https://gorosoft.com',
    'depends': [
        'base',
        'portal',
        'hr',
        'hr_holidays',  # Standard leave request management
        'mail',
        'hr_timesheet',  # For timesheet functionality
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
        'views/employee_dashboard_views.xml',
        'views/timesheet_payslip_views.xml',
        'views/leave_request_portal_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'employee_portal_hub/static/src/js/employee_portal.js',
            'employee_portal_hub/static/src/scss/employee_portal.scss',
        ],
    },
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
    'sequence': 10,
}
