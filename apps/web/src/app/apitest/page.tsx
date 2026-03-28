"use client";

import React, { useState } from 'react';

export default function ApiTestPage() {
  const [lat, setLat] = useState("14.6395");
  const [lon, setLon] = useState("121.0775");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const IP_ADDRESS = "121.58.232.219"; 

  const runTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://${IP_ADDRESS}:/analyze?latitude=${lat}&longitude=${lon}`);
      
      if (!response.ok) {
        throw new Error(`HTTP Error! Status: ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err: any) {
      setError(err.message);
      console.error("Test Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-10 bg-slate-900 min-h-screen text-white font-mono">
      <h1 className="text-2xl font-bold text-green-400 mb-6">🚀 Sentinel API Debugger</h1>
      
      <div className="flex gap-4 mb-8 bg-slate-800 p-6 rounded-lg border border-slate-700">
        <div>
          <label className="block text-xs text-slate-400 mb-1">LATITUDE</label>
          <input 
            value={lat} 
            onChange={(e) => setLat(e.target.value)}
            className="bg-slate-900 border border-slate-600 px-3 py-2 rounded text-white"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">LONGITUDE</label>
          <input 
            value={lon} 
            onChange={(e) => setLon(e.target.value)}
            className="bg-slate-900 border border-slate-600 px-3 py-2 rounded text-white"
          />
        </div>
        <button 
          onClick={runTest}
          disabled={loading}
          className="mt-5 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-bold disabled:opacity-50"
        >
          {loading ? "FETCHING..." : "FETCH DATA"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 p-4 rounded mb-6 text-red-200">
          <strong>Error:</strong> {error}
          <p className="text-xs mt-2">Check: Is FastAPI running? Is CORS enabled? Is the URL correct?</p>
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-black p-4 rounded border border-green-500/30">
            <h2 className="text-green-400 mb-2 underline">RAW JSON RESPONSE</h2>
            <pre className="text-xs overflow-auto max-h-[500px]">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>

          <div className="space-y-4">
            <h2 className="text-indigo-400 underline">DATA MAPPING CHECK</h2>
            <div className="bg-slate-800 p-4 rounded">
              <p>NDVI: <span className="text-yellow-400">{data.indices?.NDVI}</span></p>
              <p>NDWI: <span className="text-blue-400">{data.indices?.NDWI}</span></p>
            </div>
            <div className="bg-slate-800 p-4 rounded text-sm">
              <p className="font-bold border-b border-slate-700 mb-2">Urban Planning Assessment:</p>
              <p className="italic text-slate-300">
                {data.consultant_report?.urban_planning?.assessment || "Not found in JSON"}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}