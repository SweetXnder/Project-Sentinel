"use client";
import React from 'react';
import { useSentinel } from '@/context/SentinelContext';
import { Leaf, Droplets, Building2, CloudRain } from 'lucide-react';

export function LeftSidebar() {
  // Grab the data and loading state directly from your Context
  const { data, loading } = useSentinel();

  // Helper to format the numbers safely
  const formatValue = (val: number | undefined) => {
    if (loading) return "---";
    return val !== undefined ? val.toFixed(4) : "[NaN]";
  };

  const metrics = [
    {
      label: "NDVI (Vegetation Health)",
      value: formatValue(data?.metadata.NDVI),
      icon: <Leaf size={14} />,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
    },
    {
      label: "NDWI (Water/Flood Risk)",
      value: formatValue(data?.metadata.NDWI),
      icon: <Droplets size={14} />,
      color: "text-cyan-600",
      bg: "bg-cyan-50",
    },
    {
      label: "NDBI (Urban Density)",
      value: formatValue(data?.metadata.NDBI),
      icon: <Building2 size={14} />,
      color: "text-orange-700",
      bg: "bg-orange-50",
    },
    {
      label: "NDMI (Moisture Index)",
      value: formatValue(data?.metadata.NDMI),
      icon: <CloudRain size={14} />,
      color: "text-teal-600",
      bg: "bg-teal-50",
    },
  ];

  return (
    <aside className="w-72 bg-white border-r border-emerald-100 p-6 space-y-8 overflow-y-auto hidden lg:block">
      <section>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-[10px] font-bold text-emerald-800/50 uppercase tracking-[0.2em]">
            Satellite Analytics
          </h3>
          {loading && <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />}
        </div>

        <div className="space-y-4">
          {metrics.map((metric, idx) => (
            <div 
              key={idx} 
              className="group p-4 bg-white rounded-2xl border border-emerald-50 shadow-sm hover:shadow-md hover:border-emerald-200 transition-all duration-200"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className={`p-1.5 rounded-lg ${metric.bg} ${metric.color}`}>
                  {metric.icon}
                </div>
                <p className="text-[11px] text-emerald-700/70 font-bold uppercase tracking-tight">
                  {metric.label}
                </p>
              </div>
              <p className={`text-2xl font-black tabular-nums tracking-tight ${metric.color}`}>
                {metric.value}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Optional: Add a Quality Indicator since it's in your SentinelResponse */}
      {data?.metadata.quality && (
        <div className="mt-auto p-4 bg-emerald-900 rounded-2xl text-white">
          <p className="text-[10px] font-bold text-emerald-300 uppercase mb-1">Data Quality</p>
          <p className="text-sm font-medium capitalize">{data.metadata.quality}</p>
        </div>
      )}
    </aside>
  );
}