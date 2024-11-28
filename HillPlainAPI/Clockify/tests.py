import json
from unittest.mock import patch, AsyncMock
from django.test import TestCase
from httpx import AsyncClient
from django.urls import reverse
from django.http import JsonResponse
from Clockify.models import Entry  # Replace `myapp` and `Entry` with your actual app name and model.


class EntryViewTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse('HpClockifyApi/Entry')
        self.secret = 'e2kRQ3xauRrfFqkyBMsgRaCLFagJqmCE'
        self.secret2 = 'Ps4GN6oxDKYh9Q33F1BULtCI7rcgxqXW'
        self.secret3 = '0IQNBiGEAejNMlFmdQc8NWEiMe1Uzg01'
        self.headers = {
            'Authorization': f'Bearer {self.secret}'
        }
        self.valid_data = {
            "id": "6748c535977d76562d1f6946",
            "description": "Attended Affordable Housing Presentation by Steve Pomeroy at EPL",
            "userId": "65dcdd57ea15ab53ab7b14dd",
            "billable": False,
            "projectId": "65c262c0edeea53ae1a27b84",
            "timeInterval": {
                "start": "2024-11-28T15:00:00Z",
                "end": "2024-11-28T18:45:00Z",
                "duration": "PT3H45M"
            },
            "workspaceId": "65c249bfedeea53ae19d7dad",
            "isLocked": False,
            "hourlyRate": None,
            "costRate": None,
            "customFieldValues": [],
            "type": "REGULAR",
            "kioskId": None,
            "approvalStatus": None,
            "projectCurrency": None,
            "currentlyRunning": False,
            "project": {
                "name": "000-000 - Overhead (Non Billable)",
                "clientId": "65c25ae977682a2076d96d49",
                "workspaceId": "65c249bfedeea53ae19d7dad",
                "billable": False,
                "estimate": {
                    "estimate": "PT0S",
                    "type": "AUTO"
                },
                "color": "#03A9F4",
                "archived": False,
                "clientName": "Hill Plain Internal",
                "duration": "PT18938H16M48S",
                "note": "",
                "activeEstimate": "NONE",
                "timeEstimate": {
                    "includeNonBillable": True,
                    "estimate": 0,
                    "type": "AUTO",
                    "resetOption": None
                },
                "budgetEstimate": None,
                "estimateReset": None,
                "id": "65c262c0edeea53ae1a27b84",
                "public": True,
                "template": False
            },
            "task": None,
            "user": {
                "id": "65dcdd57ea15ab53ab7b14dd",
                "name": "Tyler Radke",
                "status": "ACTIVE"
            },
            "tags": []
        }

    @patch('Clockify.views.processEntryAsync', new_callable=AsyncMock)
    def test_valid_post_request(self, mock_process_entry):
        """Test a valid POST request."""
        mock_process_entry.return_value = True

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            headers=self.headers,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 202)
        mock_process_entry.assert_called_once_with(self.valid_data, 'POST')


'''
    @patch('myapp.views.processEntryAsync', new_callable=AsyncMock)
    def test_invalid_authentication(self, mock_process_entry):
        """Test request with invalid authentication."""
        headers = {
            'Authorization': 'Bearer invalid_secret'
        }

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            headers=headers,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 423)
        self.assertIn('Invalid Request', json.loads(response.content))

    def test_method_not_allowed(self):
        """Test method not allowed."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertIn('Inalid Method', json.loads(response.content))

    @patch('myapp.views.processEntryAsync', new_callable=AsyncMock)
    def test_deadlock_handling(self, mock_process_entry):
        """Test deadlock handling."""
        mock_process_entry.side_effect = Exception('deadlocked')

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            headers=self.headers,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn('deadlocked', json.loads(response.content)['Message'])

    @patch('myapp.views.processEntryAsync', new_callable=AsyncMock)
    def test_process_entry_failure(self, mock_process_entry):
        """Test processing failure."""
        mock_process_entry.return_value = False

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            headers=self.headers,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Post Data could not be validated', json.loads(response.content))

    def test_max_retries_exceeded(self):
        """Test max retries exceeded."""
        # Mock the `pauseOnDeadlock` to force retries.
        with patch('myapp.views.pauseOnDeadlock', new_callable=AsyncMock, return_value=False):
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                headers=self.headers,
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn('Failed to process request after multiple attempts', json.loads(response.content))
'''


class ProjectsViewTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse('projects')
        self.secret = 'e2kRQ3xauRrfFqkyBMsgRaCLFagJqmCE'
        self.secret2 = 'Ps4GN6oxDKYh9Q33F1BULtCI7rcgxqXW'
        self.secret3 = '0IQNBiGEAejNMlFmdQc8NWEiMe1Uzg01'
        self.headers = {
            'Authorization': f'Bearer {self.secret}'
        }
        self.valid_data = {
            "id": "6748cbcd33172a016986cdb0",
            "name": "000-000 - Test Project",
            "hourlyRate": {
                "amount": 0
            },
            "costRate": None,
            "clientId": "65c25ae977682a2076d96d49",
            "workspaceId": "65c249bfedeea53ae19d7dad",
            "billable": True,
            "memberships": [
                {
                    "userId": "65bd6a6077682a20767a6c0b",
                    "hourlyRate": None,
                    "costRate": None,
                    "targetId": "6748cbcd33172a016986cdb0",
                    "membershipType": "PROJECT",
                    "membershipStatus": "ACTIVE"
                }
            ],
            "color": "#AB47BC",
            "estimate": {
                "estimate": "PT0S",
                "type": "AUTO"
            },
            "archived": False,
            "duration": "PT0S",
            "clientName": "Hill Plain Internal",
            "note": "",
            "timeEstimate": {
                "estimate": "PT0S",
                "type": "AUTO",
                "resetOption": None,
                "active": False,
                "includeNonBillable": True
            },
            "budgetEstimate": None,
            "estimateReset": None,
            "currency": None,
            "template": False,
            "public": True,
            "tasks": [],
            "client": {
                "name": "Hill Plain Internal",
                "email": None,
                "address": "",
                "workspaceId": "65c249bfedeea53ae19d7dad",
                "archived": False,
                "note": "",
                "currencyId": {
                    "timestamp": 1707858011,
                    "date": 1707858011000
                },
                "id": "65c25ae977682a2076d96d49"
            }
        }

    @patch('Clockify.views.ProjectsView', new_callable=AsyncMock)
    async def test_valid_project_request(self, mock_project):
        """Test a valid POST request."""
        mock_project.return_value = True

        response = await self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            headers=self.headers,
            # headers={'Content-Type': 'application/json'},
            # content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        mock_project.assert_called_once_with(self.valid_data, 'POST')
