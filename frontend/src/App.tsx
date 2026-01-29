import React, { useState } from 'react';
import DeputadoSearch from './components/DeputadoSearch';
import DeputadoDetails from './components/DeputadoDetails';
import ProposicoesRelevantes from './components/ProposicoesRelevantes';
import AnaliseAvancada from './components/AnaliseAvancada';
import VotacoesRecentes from './components/VotacoesRecentes';
import { Deputado } from './types/api';

type ViewType = 'search' | 'proposicoes' | 'analise' | 'votacoes' | 'details';

const navItems = [
  { id: 'search' as ViewType, label: 'Buscar Deputados', icon: SearchIcon },
  { id: 'proposicoes' as ViewType, label: 'Proposições', icon: DocumentIcon },
  { id: 'analise' as ViewType, label: 'Análise Avançada', icon: ChartIcon },
  { id: 'votacoes' as ViewType, label: 'Votações Recentes', icon: ClockIcon },
];

function App(): React.ReactElement {
  const [currentView, setCurrentView] = useState<ViewType>('search');
  const [selectedDeputado, setSelectedDeputado] = useState<Deputado | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Persist search state across page changes
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<Deputado[]>([]);

  const handleSelectDeputado = (deputado: Deputado): void => {
    setSelectedDeputado(deputado);
    setCurrentView('details');
  };

  const handleBack = (): void => {
    setSelectedDeputado(null);
    setCurrentView('search');
  };

  const handleNavigation = (view: ViewType): void => {
    setCurrentView(view);
    setSelectedDeputado(null);
  };

  const renderContent = (): React.ReactElement => {
    switch (currentView) {
      case 'proposicoes':
        return <ProposicoesRelevantes />;
      case 'analise':
        return <AnaliseAvancada deputadoId={selectedDeputado?.id} />;
      case 'votacoes':
        return <VotacoesRecentes />;
      case 'details':
        return selectedDeputado ? (
          <DeputadoDetails deputado={selectedDeputado} onBack={handleBack} />
        ) : (
          <DeputadoSearch
            onSelectDeputado={handleSelectDeputado}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchResults={searchResults}
            setSearchResults={setSearchResults}
          />
        );
      case 'search':
      default:
        return (
          <DeputadoSearch
            onSelectDeputado={handleSelectDeputado}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchResults={searchResults}
            setSearchResults={setSearchResults}
          />
        );
    }
  };

  const getPageTitle = (): string => {
    switch (currentView) {
      case 'proposicoes': return 'Proposições Relevantes';
      case 'analise': return 'Análise Avançada';
      case 'votacoes': return 'Votações Recentes';
      case 'details': return selectedDeputado?.nome || 'Detalhes do Deputado';
      default: return 'Buscar Deputados';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 transform transition-transform duration-200 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-200">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 text-white font-bold text-lg">
            V
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900">VotoDB</h1>
            <p className="text-xs text-slate-500">Sistema de Análise</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const isActive = currentView === item.id || (item.id === 'search' && currentView === 'details');
            return (
              <button
                key={item.id}
                onClick={() => handleNavigation(item.id)}
                className={`w-full ${isActive ? 'nav-item-active' : 'nav-item-inactive'}`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-200">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-slate-50">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-700">
              <DatabaseIcon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-700 truncate">Dados Abertos</p>
              <p className="text-xs text-slate-500">Câmara dos Deputados</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-sm border-b border-slate-200">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
              >
                <MenuIcon className="w-5 h-5" />
              </button>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">{getPageTitle()}</h2>
                <p className="text-sm text-slate-500">
                  {currentView === 'search' && 'Encontre e analise deputados federais'}
                  {currentView === 'proposicoes' && 'Gerencie proposições de alta relevância'}
                  {currentView === 'analise' && 'Análise detalhada de perfil de votação'}
                  {currentView === 'votacoes' && 'Acompanhe as votações em tempo real'}
                  {currentView === 'details' && 'Visualize o histórico de votações'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                <span className="w-2 h-2 mr-2 rounded-full bg-emerald-500 animate-pulse"></span>
                API Online
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {renderContent()}
        </main>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}

// Icon components
function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function DatabaseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  );
}

export default App;
