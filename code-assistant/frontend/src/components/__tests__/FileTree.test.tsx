import { describe, it, expect, vi } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/react';
import FileTree from '../FileTree';
import * as api from '../../api';

vi.mock('../../api');

describe('FileTree', () => {
  it('opens file on double click', async () => {
    (api.listFiles as any).mockResolvedValueOnce({ files: [ { name: 'a.txt', path: 'a.txt', type: 'file' } ] });
    const onOpen = vi.fn();
    const { getByText } = render(<FileTree onOpen={onOpen} />);
    await waitFor(() => getByText('a.txt'));
    fireEvent.doubleClick(getByText('a.txt'));
    expect(onOpen).toHaveBeenCalledWith('a.txt');
  });
});
