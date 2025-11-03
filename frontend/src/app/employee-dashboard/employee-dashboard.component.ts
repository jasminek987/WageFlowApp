// src/app/employee-dashboard/employee-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService, Me, Timesheet, Payslip } from '../services/auth.service';

@Component({
  selector: 'app-employee-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './employee-dashboard.component.html'
})
export class EmployeeDashboardComponent implements OnInit {
  constructor(private auth: AuthService, private router: Router) {}

  // tabs
  activeTab: 'timesheets' | 'payslips' | 'profile' = 'timesheets';
  setTab = (t: 'timesheets' | 'payslips' | 'profile') => { this.activeTab = t; };

  // filters
  selectedMonthISO = this.toMonth(new Date());
  onMonthChange = (v: string) => { this.selectedMonthISO = v; this.computeQuickStats(); };
  searchText = '';
  onSearchChange = (v: string) => { this.searchText = v; };

  // data
  me: Me | null = null;
  timesheets: Timesheet[] = [];
  payslips: Payslip[] = [];

  // NEW: which payslip to preview on the right
  selectedPayslip: Payslip | null = null;

  // quick summary
  approvedHoursThisMonth = 0;
  pendingTimesheets = 0;

  // ui
  loading = false;
  error = '';

  ngOnInit(): void {
    if (!this.auth.token()) { this.router.navigate(['/']); return; }
    this.loadAll();
  }

  async loadAll() {
    this.loading = true;
    this.error = '';
    try {
      this.me = await firstValueFrom(this.auth.getMe());
      this.timesheets = await firstValueFrom(this.auth.getMyTimesheets());
      this.payslips = await firstValueFrom(this.auth.getMyPayslips()); // normalized by service

      // NEW: default the preview to the latest payslip (if any)
      this.selectedPayslip = this.lastPayslip;

      this.computeQuickStats();
    } catch (e: any) {
      if (e?.status === 401) { this.router.navigate(['/']); return; }
      this.error = e?.error?.message || e?.message || 'Load failed';
      console.error('[EMP] Load error', e);
    } finally {
      this.loading = false;
    }
  }

  // list getters
  get filteredTimesheets() {
    const q = this.searchText.trim().toLowerCase();
    return this.timesheets.filter(t =>
      (!q || t.weekStart.includes(q)) &&
      (!this.selectedMonthISO || t.weekStart.slice(0, 7) <= this.selectedMonthISO)
    );
  }

  get filteredPayslips() {
    const q = this.searchText.trim().toLowerCase();
    const month = this.selectedMonthISO;
    return this.payslips.filter(p => {
      const startIso = (p as any).start ?? p.period.split(' to ')[0];
      const inMonth = !month || startIso.slice(0, 7) <= month;
      const matches = !q || p.period.toLowerCase().includes(q);
      return inMonth && matches;
    });
  }

  // latest payslip helper
  get lastPayslip(): Payslip | null {
    if (!this.payslips?.length) return null;
    return this.payslips[this.payslips.length - 1];
  }

  // NEW: called from the payslip table row (click)
  selectPayslip(p: Payslip) {
    this.selectedPayslip = p;
  }

  // stats
  private computeQuickStats() {
    const month = this.selectedMonthISO;
    this.approvedHoursThisMonth = this.timesheets
      .filter(t => t.status === 'approved' && t.weekStart.slice(0, 7) === month)
      .reduce((s, t) => s + t.hours, 0);
    this.pendingTimesheets = this.timesheets.filter(t => t.status === 'pending').length;
  }

  // misc
  trackById = (_: number, x: { id: number }) => x.id;

  private toMonth(d: Date) {
    const m = (d.getMonth() + 1).toString().padStart(2, '0');
    return `${d.getFullYear()}-${m}`;
  }

  onLogout() {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
