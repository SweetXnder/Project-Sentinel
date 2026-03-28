interface LeftSidebarProps {
  dvi: string;
  ndwi: string;
  ndbi: string;
  ndmi: string;
}

export function LeftSidebar({ dvi, ndwi, ndbi, ndmi }: LeftSidebarProps) {
  return (
    <aside className="w-64 bg-slate-100 border-r border-slate-200 p-6 space-y-8 overflow-y-auto">
      <section>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Quick Stats</h3>
        <div className="space-y-4">
          <div className="p-3 bg-white rounded-lg shadow-sm border border-slate-200">
            <p className="text-xs text-slate-500 font-semibold">DVI (Vegetation Health)</p>
            <p className="text-xl font-bold text-green-600">{dvi}</p>
          </div>
          <div className="p-3 bg-white rounded-lg shadow-sm border border-slate-200">
            <p className="text-xs text-slate-500 font-semibold">NDWI (Water/Flood Risk)</p>
            <p className="text-xl font-bold text-blue-600">{ndwi}</p>
          </div>
          <div className="p-3 bg-white rounded-lg shadow-sm border border-slate-200">
            <p className="text-xs text-slate-500 font-semibold">NDBI (Urban Density)</p>
            <p className="text-xl font-bold text-gray-600">{ndbi}</p>
          </div>
          <div className="p-3 bg-white rounded-lg shadow-sm border border-slate-200">
            <p className="text-xs text-slate-500 font-semibold">NDMI (Moisture Index)</p>
            <p className="text-xl font-bold text-teal-600">{ndmi}</p>
          </div>
        </div>
      </section>  
    </aside>
  );
}