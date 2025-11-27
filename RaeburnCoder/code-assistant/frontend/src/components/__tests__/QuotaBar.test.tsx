import { describe, it, expect, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import QuotaBar from '../QuotaBar';
import * as api from '../../api';

vi.mock('../../api');

describe('QuotaBar', () => {
  it('renders quota usage', async () => {
    (api.getQuota as any).mockResolvedValue({ used: 10, limit: 100 });
    const { container } = render(<QuotaBar />);
    await waitFor(() => {
      const bar = container.querySelector('div div');
      expect(bar?.getAttribute('style')).toContain('10%');
    });
  });
});
