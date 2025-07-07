# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.depends('project_id', 'name')
    def _compute_safe_display_name(self):
        """Compute a safe display name that doesn't trigger project access errors"""
        for record in self:
            try:
                if record.project_id:
                    # Try to access project name safely
                    record.safe_display_name = record.project_id.name
                else:
                    record.safe_display_name = record.name or 'Timesheet Entry'
            except AccessError:
                # User doesn't have project access, use timesheet name instead
                record.safe_display_name = record.name or 'Timesheet Entry'
            except:
                # Any other error, use fallback
                record.safe_display_name = record.name or 'Timesheet Entry'

    safe_display_name = fields.Char(
        string='Safe Display Name',
        compute='_compute_safe_display_name',
        store=False,
        help="Display name that safely handles project access restrictions"
    )

    def get_safe_project_name(self):
        """Get project name safely without triggering access errors"""
        try:
            if self.project_id:
                return self.project_id.name
            return self.name or 'Timesheet Entry'
        except AccessError:
            return self.name or 'Timesheet Entry'
        except:
            return self.name or 'Timesheet Entry'
