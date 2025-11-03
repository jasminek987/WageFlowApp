import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AuthService, Employee, Timesheet } from '../services/auth.service';
import { Router } from '@angular/router';

type Status = 'pending' | 'approved';

@Component({
  selector: 'app-manager-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './manager-dashboard.component.html',
})
export class ManagerDashboardComponent implements OnInit {
  // UI state
  loading = false;
  error = '';

  // filters/search
  statusFilter: Status | 'all' = 'pending';
  searchText = '';

  // live data
  employees: Employee[] = [];
  timesheets: (Timesheet & { status: Status })[] = [];

  // stats
  pendingCount = 0;
  totalEmployees = 0;
  shownPayroll = 0;

  // modal
  showAdd = false;
  newEmp: Partial<Employee> = { name: '', email: '', rate: 0 };

  // prevent double-approve clicks
  approving = new Set<number>();

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    if (!this.auth.token()) { this.router.navigate(['/']); return; }
    this.refresh(true); // latestOnly
  }

  private norm = (s: any): Status =>
    String(s || '').toLowerCase() === 'approved' ? 'approved' : 'pending';

  // map name
  empName = (id: number) => this.employees.find(e => e.id === id)?.name ?? '—';

  get filteredTimesheets() {
    const base =
      this.statusFilter === 'all'
        ? this.timesheets
        : this.timesheets.filter(t => t.status === this.statusFilter);

    const q = this.searchText.trim().toLowerCase();
    return q
      ? base.filter(t => this.empName(t.employeeId).toLowerCase().includes(q))
      : base;
  }
async approve(id: number) {
  const idx = this.timesheets.findIndex(t => t.id === id);
  if (idx < 0) return;

  const prev = { ...this.timesheets[idx] };

  // optimistic update
  this.timesheets[idx].status = 'approved' as const;

  // if you're viewing the Pending tab, hide it immediately
  if (this.statusFilter === 'pending') {
    this.timesheets = this.timesheets.filter(t => t.id !== id);
  }
  this.updateStats();

  try {
    await firstValueFrom(this.auth.approveTimesheet(id));
  } catch (e: any) {
    // rollback on failure
    const pos = this.timesheets.findIndex(t => t.id === id);
    if (pos >= 0) this.timesheets[pos] = prev; else this.timesheets.push(prev);
    this.updateStats();
    this.error = e?.error?.message || e?.message || 'Approve failed';
  }
}


  async refresh(latestOnly = false) {
    this.loading = true;
    this.error = '';
    try {
      const [emps, ts] = await Promise.all([
        firstValueFrom(this.auth.getEmployees()),
        firstValueFrom(this.auth.getTimesheets(latestOnly)), // service should add ?latest=1 when true
      ]);

      this.employees = emps ?? [];

      const normalized = (ts ?? []).map(t => ({
        ...t,
        status: this.norm((t as any).status),
      })) as (Timesheet & { status: Status })[];

      this.timesheets = normalized;
      this.totalEmployees = this.employees.length;
      this.updateStats();
    } catch (e: any) {
      if (e?.status === 401) { this.router.navigate(['/']); return; }
      this.error = e?.error?.message || e?.message || 'Failed to load data';
    } finally {
      this.loading = false;
    }
  }

  exportCsv() {
    const rows = [
      ['ID', 'Employee', 'WeekStart', 'Hours', 'Status'],
      ...this.filteredTimesheets.map(t => [
        t.id,
        this.empName(t.employeeId),
        t.weekStart,
        t.hours,
        t.status,
      ]),
    ];
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'timesheets.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  openAdd() { this.showAdd = true; }
  closeAdd() { this.showAdd = false; }

  async addEmployee() {
    if (!this.newEmp.name || !this.newEmp.email || !this.newEmp.rate) return;
    try {
      this.loading = true;
      const created = await firstValueFrom(
        this.auth.createEmployee({
          name: this.newEmp.name!,
          email: this.newEmp.email!,
          rate: Number(this.newEmp.rate),
        })
      );
      this.employees.push(created);
      this.totalEmployees = this.employees.length;
      this.showAdd = false;
      this.newEmp = { name: '', email: '', rate: 0 };
      this.updateStats();
    } catch (e: any) {
      this.error = e?.error?.message || e?.message || 'Add employee failed';
    } finally {
      this.loading = false;
    }
  }

  updateStats() {
    this.pendingCount = this.timesheets.filter(t => t.status === 'pending').length;
    const base = this.filteredTimesheets;
    this.shownPayroll = base.reduce((sum, t) => {
      const e = this.employees.find(x => x.id === t.employeeId);
      return e ? sum + e.rate * t.hours : sum;
    }, 0);
  }

  onLogout() {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
