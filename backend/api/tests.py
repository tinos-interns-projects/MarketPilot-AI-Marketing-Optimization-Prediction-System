from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import os
import numpy as np

from .model_loader import predict_campaign, calculate_campaign_roi


class TestPredictCampaign(TestCase):
    def setUp(self):
        self.valid_data = {'Spend': 2000, 'Campaign_Duration': 14, 'Daily_Spend': 142.86}

    def test_predict_campaign_valid_input(self):
        prob, decision = predict_campaign(self.valid_data)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)
        self.assertIn(decision, ['Increase Budget', 'Test Campaign', 'Avoid Campaign'])

    def test_predict_campaign_zero_duration(self):
        data = {'Spend': 2000, 'Campaign_Duration': 0, 'Daily_Spend': 2000}
        prob, decision = predict_campaign(data)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_predict_campaign_high_spend(self):
        data = {'Spend': 10000, 'Campaign_Duration': 30, 'Daily_Spend': 333.33}
        prob, decision = predict_campaign(data)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)


class TestPredictAPIView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.predict_url = reverse('predict')
        self.valid_payload = {'Channel': 'Google', 'Campaign_Duration': 30, 'Spend': 2000}

    def test_predict_get_request(self):
        response = self.client.get(self.predict_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('probability', response.data)
        self.assertIn('decision', response.data)
        self.assertIn('channel', response.data)
        self.assertIn('kpis', response.data)
        self.assertIn('input', response.data)

    def test_predict_post_request_valid_data(self):
        response = self.client.post(self.predict_url, data=self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('probability', response.data)
        self.assertIn('decision', response.data)
        self.assertIn('channel', response.data)
        self.assertIn('kpis', response.data)
        self.assertIn('input', response.data)
        prob = response.data['probability']
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)
        self.assertIn(response.data['decision'], ['Increase Budget', 'Test Campaign', 'Avoid Campaign'])

    def test_predict_response_structure(self):
        response = self.client.post(self.predict_url, data=self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        expected_keys = ['probability', 'decision', 'channel', 'kpis', 'input']
        self.assertEqual(sorted(response.data.keys()), sorted(expected_keys))

    def test_predict_with_various_inputs(self):
        test_cases = [
            {'Channel': 'Google', 'Campaign_Duration': 30, 'Spend': 5000},
            {'Channel': 'Facebook', 'Campaign_Duration': 14, 'Spend': 1000},
        ]
        for payload in test_cases:
            response = self.client.post(self.predict_url, data=payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('probability', response.data)
            self.assertIn('decision', response.data)


class TestCalculateKPIs(TestCase):
    def test_daily_spend_calculation(self):
        spend = 2000
        duration = 30
        expected_daily = spend / duration
        self.assertAlmostEqual(expected_daily, 66.67, places=1)

    def test_campaign_roi_calculation(self):
        metrics = calculate_campaign_roi(2000, 30, conversions=50)
        self.assertIn('ROI', metrics)
        self.assertIn('revenue', metrics)
        self.assertGreater(metrics['ROI'], 0)


@override_settings(
    MODEL_PATH=os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'model.pkl'),
    SCALER_PATH=os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'scaler.pkl')
)
class TestModelFiles(TestCase):
    def test_model_file_exists(self):
        model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'model.pkl')
        self.assertTrue(os.path.exists(model_path))

    def test_scaler_file_exists(self):
        scaler_path = os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'scaler.pkl')
        self.assertTrue(os.path.exists(scaler_path))

    def test_model_can_predict(self):
        data = {'Spend': 2000, 'Campaign_Duration': 14, 'Daily_Spend': 142.86}
        prob, decision = predict_campaign(data)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)
        self.assertIn(decision, ['Increase Budget', 'Test Campaign', 'Avoid Campaign'])
