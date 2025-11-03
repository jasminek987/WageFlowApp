// frontend/src/app/app-routing.module.ts
import { NgModule } from '@angular/core';
import { RouterModule, Routes, CanActivate } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { EmployeeDashboardComponent } from './employee-dashboard/employee-dashboard.component';
import { ManagerDashboardComponent } from './manager-dashboard/manager-dashboard.component';

class RoleGuard implements CanActivate {
  constructor(private wanted: 'EMPLOYEE' | 'MANAGER') {}
  canActivate(): boolean {
    const role = localStorage.getItem('role');
    const token = localStorage.getItem('token');
    return !!token && role === this.wanted;
  }
}
// app-routing.module.ts
const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'employee-dashboard', component: EmployeeDashboardComponent }, // ← no guard for now
  { path: 'manager-dashboard', component: ManagerDashboardComponent },   // ← no guard for now
  { path: '**', redirectTo: 'login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
