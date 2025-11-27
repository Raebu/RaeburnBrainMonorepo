import React, { useEffect, useState } from 'react';
import { getQuota } from '../api';

export default function QuotaBar() {
  const [quota, setQuota] = useState<{used:number, limit:number}>({used:0, limit:1});

  useEffect(() => {
    async function fetchQuota() {
      try {
        const res = await getQuota();
        setQuota(res);
      } catch {
        // ignore
      }
    }
    fetchQuota();
    const id = setInterval(fetchQuota, 5000);
    return () => clearInterval(id);
  }, []);

  const pct = Math.min(quota.used / quota.limit, 1);

  return (
    <div className="h-2 bg-gray-700 w-full">
      <div className="bg-green-600 h-full" style={{ width: `${pct * 100}%` }} />
    </div>
  );
}
