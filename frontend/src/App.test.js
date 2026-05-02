import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import '@testing-library/jest-dom';

jest.mock('axios');
const mockAxios = require('axios');

describe('App', () => {
  beforeEach(() => {
    mockAxios.post.mockClear();
  });

  test('renders Dashboard component', () => {
    render(<App />);
    expect(screen.getByText(/Marketing Intelligence Dashboard/i)).toBeInTheDocument();
  });

  test('renders all input fields and buttons', () => {
    render(<App />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Campaign Duration/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Total Budget/i)).toBeInTheDocument();
    const predictBtns = screen.getAllByText('Predict');
    expect(predictBtns.length).toBeGreaterThan(0);
  });

  test('renders KPI cards', () => {
    render(<App />);
    expect(screen.getByText(/Daily Spend/i)).toBeInTheDocument();
    expect(screen.getByText(/Est\. ROI/i)).toBeInTheDocument();
    const headings = screen.getAllByRole('heading');
    expect(headings.some(h => h.textContent === 'Decision')).toBe(true);
  });

  test('renders chart section', () => {
    render(<App />);
    expect(screen.getByText(/ROI by Channel/i)).toBeInTheDocument();
  });

  test('handles input changes correctly', () => {
    render(<App />);
    const channelSelect = screen.getByRole('combobox');
    fireEvent.change(channelSelect, { target: { value: 'Facebook' } });
    expect(channelSelect.value).toBe('Facebook');
    const durationInput = screen.getByPlaceholderText(/Campaign Duration/i);
    fireEvent.change(durationInput, { target: { value: '30' } });
    expect(durationInput.value).toBe('30');
    const spendInput = screen.getByPlaceholderText(/Total Budget/i);
    fireEvent.change(spendInput, { target: { value: '2000' } });
    expect(spendInput.value).toBe('2000');
  });

  test('makes prediction API call on button click', async () => {
    mockAxios.post.mockResolvedValue({
      data: {
        probability: 0.85,
        decision: 'Increase Budget',
        channel: 'Google',
        kpis: {
          daily_spend: 66.67,
          total_spend: 2000,
          duration: 30,
          estimated_roi: 1.5,
          estimated_conversions: 25.5
        },
        input: {
          channel: 'Google',
          duration: 30,
          spend: 2000
        }
      }
    });
    render(<App />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Google' } });
    fireEvent.change(screen.getByPlaceholderText(/Campaign Duration/i), { target: { value: '30' } });
    fireEvent.change(screen.getByPlaceholderText(/Total Budget/i), { target: { value: '2000' } });
    const predictButton = screen.getAllByRole('button')[0];
    fireEvent.click(predictButton);
    await waitFor(() => {
      expect(mockAxios.post).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/predict/',
        expect.objectContaining({
          Channel: 'Google',
          Campaign_Duration: 30,
          Spend: 2000
        })
      );
    });
  });

  test('displays prediction results', async () => {
    mockAxios.post.mockResolvedValue({
      data: {
        probability: 0.85,
        decision: 'Increase Budget',
        channel: 'Facebook',
        kpis: {
          daily_spend: 142.86,
          total_spend: 2000,
          duration: 14,
          estimated_roi: 1.5,
          estimated_conversions: 25.5
        },
        input: {
          channel: 'Facebook',
          duration: 14,
          spend: 2000
        }
      }
    });
    render(<App />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Facebook' } });
    fireEvent.change(screen.getByPlaceholderText(/Campaign Duration/i), { target: { value: '14' } });
    fireEvent.change(screen.getByPlaceholderText(/Total Budget/i), { target: { value: '2000' } });
    const predictButton = screen.getAllByRole('button')[0];
    fireEvent.click(predictButton);
    await waitFor(() => {
      expect(screen.getByText(/0.85/i)).toBeInTheDocument();
      expect(screen.getByText(/Increase Budget/i)).toBeInTheDocument();
    });
  });

  test('calculates and displays KPI values after prediction', async () => {
    mockAxios.post.mockResolvedValue({
      data: {
        probability: 0.85,
        decision: 'Increase Budget',
        channel: 'Google',
        kpis: {
          daily_spend: 66.67,
          total_spend: 2000,
          duration: 30,
          estimated_roi: 1.5,
          estimated_conversions: 25.5
        },
        input: {
          channel: 'Google',
          duration: 30,
          spend: 2000
        }
      }
    });
    render(<App />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Google' } });
    fireEvent.change(screen.getByPlaceholderText(/Campaign Duration/i), { target: { value: '30' } });
    fireEvent.change(screen.getByPlaceholderText(/Total Budget/i), { target: { value: '2000' } });
    const predictButton = screen.getAllByRole('button')[0];
    fireEvent.click(predictButton);
    await waitFor(() => {
      const cards = screen.getAllByText(/[0-9]/);
      expect(cards.length).toBeGreaterThan(0);
    });
  });
});
