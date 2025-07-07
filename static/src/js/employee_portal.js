/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

// Employee Portal Hub JavaScript
console.log('Employee Portal Hub JS loaded');

// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard features
    initializeDashboard();
    initializeQuickActions();
    initializeLeaveCalendar();
});

function initializeDashboard() {
    // Dashboard initialization logic
    console.log('Dashboard initialized');

    // Add hover effects to cards
    const cards = document.querySelectorAll('.eph_dashboard_card, .eph_stats_card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

function initializeQuickActions() {
    // Quick action functionality
    const actionBtns = document.querySelectorAll('.eph_action_btn');
    actionBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Add loading state
            this.classList.add('eph_loading');
        });
    });
}

function initializeLeaveCalendar() {
    // Leave calendar initialization
    const calendarContainer = document.querySelector('.eph_calendar_container');
    if (calendarContainer) {
        // Basic calendar placeholder
        calendarContainer.innerHTML = '<p class="text-center text-muted">Calendar will be loaded here</p>';
    }
}
