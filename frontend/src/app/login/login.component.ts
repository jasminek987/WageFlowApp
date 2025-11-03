import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent {
  email = '';
  password = '';
  errorMsg = '';
  loading = false;

  constructor(private auth: AuthService, private router: Router) {}

  onLogin() {
  this.errorMsg = '';
  if (!this.email.trim() || !this.password.trim()) {
    this.errorMsg = 'Please enter email and password.';
    return;
  }
  this.loading = true;

  this.auth.login(this.email, this.password).subscribe({
    next: (res) => {
      console.log('LOGIN OK', res);             // 👈 see the response
      if (res.role === 'manager') {
        this.router.navigate(['/manager-dashboard']);
      } else if (res.role === 'employee') {
        this.router.navigate(['/employee-dashboard']);
      } else {
        this.errorMsg = 'Unknown role.';
      }
      this.loading = false;
    },
    error: (e) => {
      console.error('LOGIN FAIL', e);           // 👈 see the error
      this.errorMsg = e?.error?.error || 'Invalid email or password.';
      this.loading = false;
    }
  });
}

}
