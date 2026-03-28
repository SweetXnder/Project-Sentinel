"use client";

import React, { createContext, useContext, ReactNode } from 'react';
import { useSentinelData, SentinelResponse } from '../hooks/useSentinelData';

// 1. Define the shape of our context
interface SentinelContextType {
  data: SentinelResponse | null;
  loading: boolean;
  error: string | null;
  analyzeLocation: (lat: number, lon: number) => Promise<void>;
}

// 2. Create the Context with a default value of undefined
const SentinelContext = createContext<SentinelContextType | undefined>(undefined);

// 3. EXPORT the Provider component
export function SentinelProvider({ children }: { children: ReactNode }) {
  const sentinel = useSentinelData();

  return (
    <SentinelContext.Provider value={sentinel}>
      {children}
    </SentinelContext.Provider>
  );
}

// 4. EXPORT the custom hook
export function useSentinel() {
  const context = useContext(SentinelContext);
  if (context === undefined) {
    throw new Error('useSentinel must be used within a SentinelProvider');
  }
  return context;
}