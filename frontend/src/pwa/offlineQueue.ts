const DB_NAME = 'vistazo_offline_db';
const STORE_NAME = 'pending_attempts';

export interface QueuedAttempt {
  client_attempt_id: string;
  challenge_id: string;
  classroom_id: string | null;
  submitted_answer: Record<string, unknown>;
  response_time_ms: number;
  queued_at: number;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB no disponible'));
      return;
    }
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'client_attempt_id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function enqueueOfflineAttempt(item: QueuedAttempt): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put(item);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function listOfflineAttempts(): Promise<QueuedAttempt[]> {
  try {
    const db = await openDb();
    return await new Promise<QueuedAttempt[]>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const req = tx.objectStore(STORE_NAME).getAll();
      req.onsuccess = () => resolve((req.result as QueuedAttempt[]) ?? []);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}

export async function removeOfflineAttempt(clientAttemptId: string): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(clientAttemptId);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function flushOfflineAttempts(
  sender: (item: QueuedAttempt) => Promise<unknown>
): Promise<number> {
  const items = await listOfflineAttempts();
  let synced = 0;
  for (const item of items) {
    try {
      await sender(item);
      await removeOfflineAttempt(item.client_attempt_id);
      synced += 1;
    } catch {
      break;
    }
  }
  return synced;
}
