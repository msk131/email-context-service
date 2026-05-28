"""Locust load testing file for Email Context Service API."""
import random
from datetime import datetime, timedelta

from locust import HttpUser, between, task


class EmailContextUser(HttpUser):
    """Simulates a user interacting with the Email Context API."""

    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Execute on user startup - login and get access token."""
        self.token = None
        self.client_id = None
        self.firm_id = None
        self.user_id = None
        self.login()

    def login(self):
        """Authenticate and get JWT token."""
        response = self.client.post(
            "/api/v1/auth/token",
            json={
                "email": "accountant@example.com",
                "password": "password123"
            },
            name="/api/v1/auth/token"
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            # Fallback test user if real auth fails
            self.token = "test-token"

    def get_headers(self):
        """Get authorization headers with JWT token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(1)
    def health_check(self):
        """Health check endpoint - baseline request."""
        self.client.get("/", name="/health")

    @task(2)
    def get_clients_list(self):
        """Get list of clients - common read operation."""
        client_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/clients/{client_id}",
            headers=self.get_headers(),
            name="/api/v1/clients/[client_id]"
        )

    @task(3)
    def get_summary(self):
        """Get email summary for a client - main operation."""
        client_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/summaries/{client_id}",
            headers=self.get_headers(),
            name="/api/v1/summaries/[client_id]"
        )

    @task(2)
    def refresh_summary(self):
        """Refresh email summary - heavier operation."""
        client_id = random.randint(1, 50)
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        self.client.post(
            f"/api/v1/summaries/{client_id}/refresh",
            headers=self.get_headers(),
            params={
                "start_date": start_date,
                "end_date": end_date,
                "force": "false"
            },
            name="/api/v1/summaries/[client_id]/refresh"
        )

    @task(1)
    def get_firm_summaries(self):
        """Get firm-level summary report."""
        self.client.get(
            "/api/v1/reports/firm-summaries",
            headers=self.get_headers(),
            name="/api/v1/reports/firm-summaries"
        )

    @task(1)
    def get_global_summaries(self):
        """Get global summary report."""
        self.client.get(
            "/api/v1/reports/global-summaries",
            headers=self.get_headers(),
            name="/api/v1/reports/global-summaries"
        )

    @task(1)
    def get_firm(self):
        """Get firm details."""
        firm_id = random.randint(1, 20)
        self.client.get(
            f"/api/v1/firms/{firm_id}",
            headers=self.get_headers(),
            name="/api/v1/firms/[firm_id]"
        )


class AdminUser(HttpUser):
    """Admin user with different access patterns."""

    wait_time = between(3, 8)

    def on_start(self):
        """Execute on user startup - admin login."""
        self.token = None
        self.login_admin()

    def login_admin(self):
        """Admin authentication."""
        response = self.client.post(
            "/api/v1/auth/token",
            json={
                "email": "admin@example.com",
                "password": "admin123"
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            self.token = "admin-test-token"

    def get_headers(self):
        """Get authorization headers with JWT token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(1)
    def get_all_firm_summaries(self):
        """Admin: View all firm summaries."""
        self.client.get(
            "/api/v1/reports/global-summaries",
            headers=self.get_headers(),
            name="/api/v1/reports/global-summaries [admin]"
        )

    @task(2)
    def force_refresh_summaries(self):
        """Admin: Force refresh summaries across multiple clients."""
        for _ in range(3):
            client_id = random.randint(1, 100)
            self.client.post(
                f"/api/v1/summaries/{client_id}/refresh",
                headers=self.get_headers(),
                params={"force": "true"},
                name="/api/v1/summaries/[client_id]/refresh [force]"
            )
