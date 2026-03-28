interface SidebarTabsProps {
  activeTab: 'risk' | 'rec';
  setActiveTab: (tab: 'risk' | 'rec') => void;
}

export const SidebarTabs = ({ activeTab, setActiveTab }: SidebarTabsProps) => (
  <div className="flex p-2 bg-slate-100 gap-1">
    {(['risk', 'rec'] as const).map((tab) => (
      <button
        key={tab}
        onClick={() => setActiveTab(tab)}
        className={`flex-1 py-2 text-xs font-bold rounded-md transition-all ${
          activeTab === tab 
            ? 'bg-white text-indigo-600 shadow-sm' 
            : 'text-slate-500 hover:bg-slate-200'
        }`}
      >
        {tab === 'risk' ? "Risk Assessment" : "Recommendations"}
      </button>
    ))}
  </div>
);