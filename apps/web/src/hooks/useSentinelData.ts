import { useState, useCallback } from 'react';

export interface SentinelResponse {
  metadata: {
    NDVI: number;
    NDWI: number;
    NDBI: number;
    NDMI: number;
    quality: string;
  };
  report: {
    report_metadata: {
      title: string;
      location: string;
      scientist_rank: string;
    };
    data_meanings: {
      [key: string]: {
        value: number;
        status: string;
        interpretation: string;
      };
    };
    deep_risk_assessment: {
      [key: string]: {
        threat_level: string;
        description: string;
      };
    };
    actionable_recommendations: {
      urban_planning: string;
      architecture: string;
      engineering: string;
      environmental: string;
      agriculture: string;
      economics: string;
    };
    citations_and_frameworks: string[];
  };
}

export const useSentinelData = () => {
  const [data, setData] = useState<SentinelResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeLocation = useCallback(async (lat: number, lon: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://127.0.0.1:8000/analyze?lat=${lat}&lon=${lon}`);
      
      if (!response.ok) throw new Error("Failed to fetch satellite data");
      
      const json: SentinelResponse = await response.json();
      setData(json);
    } catch (err: any) {
      setError(err.message);
      console.error("Analysis Error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, analyzeLocation };
};