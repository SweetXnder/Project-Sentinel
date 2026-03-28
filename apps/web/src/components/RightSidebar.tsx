"use client";
import React, { useState } from 'react';
import { Leaf, Building2, HardHat, Sprout, BarChart3, Globe } from 'lucide-react';

export const RightSidebar = () => {
  const [activeTab, setActiveTab] = useState<'risk' | 'rec'>('risk');

  const recommendations = {
    urban_planning: {
      icon: <Globe size={18} />,
      title: "Urban Planning",
      text: "Implement a 'Miyawaki Forest' model in underutilized open spaces to rapidly increase NDVI and restore native Dipterocarp species."
    },
    architecture: {
      icon: <Building2 size={18} />,
      title: "Architecture",
      text: "Integrate Biophilic Design and Green Roofs. Target BERDE certification for new structures to improve thermal insulation."
    },
    engineering: {
      icon: <HardHat size={18} />,
      title: "Engineering",
      text: "Deploy Permeable Pavement Systems and Bioswales to manage runoff suggested by the NDWI/NDBI profile."
    },
    environmental: {
      icon: <Leaf size={18} />,
      title: "Environmental",
      text: "Transition from manicured lawns to multi-story agroforestry plots to improve both NDMI and local soil health."
    },
    agriculture: {
      icon: <Sprout size={18} />,
      title: "Agriculture",
      text: "Utilize existing open spaces for edible landscaping and urban hydroponics to promote food security."
    },
    economics: {
      icon: <BarChart3 size={18} />,
      title: "Economics",
      text: "Perform a 'Natural Capital Accounting' exercise. Calculate cost-savings from reduced HVAC usage."
    }
  };

  const frameworks = [
    "UN SDG 11: Sustainable Cities",
    "UN SDG 13: Climate Action",
    "Philippine Green Building Code",
    "BERDE v4.0 Framework",
    "RA 9729: Climate Change Act",
    "IPCC AR6 Urban Mitigation"
  ];

  return (
    <aside className="w-96 bg-white border-l border-slate-200 flex flex-col overflow-hidden shadow-xl z-20">
      {/* TABS */}
      <div className="flex p-2 bg-slate-100 gap-1">
        <button
          onClick={() => setActiveTab('risk')}
          className={`flex-1 py-2 text-xs font-bold rounded-md transition-all ${
            activeTab === 'risk' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:bg-slate-200'
          }`}
        >
          Risk Assessment
        </button>
        <button
          onClick={() => setActiveTab('rec')}
          className={`flex-1 py-2 text-xs font-bold rounded-md transition-all ${
            activeTab === 'rec' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:bg-slate-200'
          }`}
        >
          Recommendations
        </button>
      </div>

      {/* SCROLLABLE CONTENT AREA */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className={`p-6 flex flex-col items-center min-h-full ${activeTab === 'risk' ? 'bg-emerald-50/30' : 'bg-indigo-50/30'}`}>
          
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">
            {activeTab === 'risk' ? "Flood Risk Level" : "Strategic Actions"}
          </h2>

          {/* LARGE CIRCULAR INDICATOR */}
          <div className="w-32 h-32 bg-white rounded-full border-4 border-white shadow-lg flex flex-col items-center justify-center mb-8 ring-1 ring-slate-200">
            <span className="text-4xl font-black text-slate-900 tracking-tighter">
              {activeTab === 'risk' ? "MOD" : "06"}
            </span>
            <span className="text-[10px] font-bold text-slate-400 uppercase">
              {activeTab === 'risk' ? "Severity" : "Tasks"}
            </span>
          </div>

          {/* RECOMMENDATION ROWS */}
          <div className="w-full space-y-3">
            {Object.entries(recommendations).map(([key, item]) => (
              <div key={key} className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm hover:border-indigo-300 transition-colors group">
                <div className="flex items-center gap-3 mb-1">
                  <div className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                    {item.icon}
                  </div>
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-tight">{item.title}</h3>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-600 italic">
                  "{item.text}"
                </p>
              </div>
            ))}
          </div>

          {/* CITATIONS / FRAMEWORKS */}
          <div className="w-full mt-8 pt-6 border-t border-slate-200">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase mb-3 tracking-widest">Compliance Frameworks</h4>
            <div className="flex flex-wrap gap-1.5">
              {frameworks.map((tag, i) => (
                <span key={i} className="text-[9px] px-2 py-1 bg-slate-200 text-slate-600 rounded-md font-medium whitespace-nowrap">
                  {tag}
                </span>
              ))}
            </div>
          </div>
          
          <p className="my-8 text-center text-[10px] text-slate-400 leading-tight">
            Generated via Sentinel-2 L2A Multispectral Instrument<br/>
            Ref: Quezon City Resilience Masterplan 2026
          </p>
        </div>
      </div>
    </aside>
  );
};