import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/react';
import GitCommitModal from '../GitCommitModal';
import * as api from '../../api';

vi.mock('../../api');

describe('GitCommitModal', () => {
  it('stages and commits files', async () => {
    (api.getGitStatus as any).mockResolvedValue({ status: [{ file: 'a.txt', status: 'M' }] });
    (api.gitAdd as any).mockResolvedValue({});
    (api.gitCommit as any).mockResolvedValue({});
    (api.gitPush as any).mockResolvedValue({});
    const onClose = vi.fn();
    const { getByText, getByPlaceholderText } = render(<GitCommitModal open onClose={onClose} />);
    await waitFor(() => getByText('a.txt'));
    fireEvent.change(getByPlaceholderText('Commit message'), { target: { value: 'msg' } });
    fireEvent.click(getByText('Commit'));
    await waitFor(() => expect(api.gitAdd).toHaveBeenCalled());
    expect(api.gitCommit).toHaveBeenCalledWith('msg');
    expect(onClose).toHaveBeenCalled();
  });
});
