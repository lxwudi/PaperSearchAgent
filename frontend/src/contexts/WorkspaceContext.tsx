import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

const STORAGE_JOB = 'ps_active_job';

export type WorkspaceContextValue = {
  activeJobId: string | null;
  setActiveJobId: (id: string | null) => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [activeJobId, setActiveJobIdState] = useState<string | null>(
    () => localStorage.getItem(STORAGE_JOB),
  );

  const setActiveJobId = (id: string | null) => {
    setActiveJobIdState(id);
    if (!id) {
      localStorage.removeItem(STORAGE_JOB);
    } else {
      localStorage.setItem(STORAGE_JOB, id);
    }
  };

  const value = useMemo(() => ({ activeJobId, setActiveJobId }), [activeJobId]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return ctx;
}

