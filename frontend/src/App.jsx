import React, { useState, useRef, useEffect } from 'react';
import { 
  Shield, 
  Activity, 
  Radio, 
  AlertTriangle, 
  MapPin, 
  Factory, 
  Cpu, 
  Database, 
  FileText, 
  Settings, 
  Globe,
  ChevronDown,
  Menu,
  X,
  Compass,
  Layers,
  Sparkles,
  LayoutDashboard,
  Home
} from 'lucide-react';
import LandingPage from './pages/LandingPage';
import MainDashboard from './pages/MainDashboard';
import MonitoringPage from './pages/MonitoringPage';
import PollutionEventsPage from './pages/PollutionEventsPage';
import EventWorkspacePage from './pages/EventWorkspacePage';
import InteractiveMapPage from './pages/InteractiveMapPage';
import SourceAttributionPage from './pages/SourceAttributionPage';
import AIAssistantPage from './pages/AIAssistantPage';
import ModelMonitoringPage from './pages/ModelMonitoringPage';
import DataSourcesPage from './pages/DataSourcesPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import RegionSelector, { REGIONS_OPTIONS } from './components/RegionSelector';

// Navigation Groups Definition (Frozen Routes)
export const NAV_GROUPS = [
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'home', label: 'Platform Intro', icon: Home },
    ]
  },
  {
    id: 'monitor',
    label: 'Monitor',
    icon: Activity,
    items: [
      { id: 'monitoring', label: 'Air Quality', icon: Activity },
      { id: 'events', label: 'Pollution Events', icon: AlertTriangle },
      { id: 'map', label: 'Geographic Map', icon: MapPin },
    ]
  },
  {
    id: 'investigate',
    label: 'Investigate',
    icon: Compass,
    items: [
      { id: 'attribution', label: 'Source Attribution', icon: Factory },
      { id: 'workspace', label: 'Investigation Workspace', icon: Compass },
      { id: 'assistant', label: 'AI Assistant', icon: Sparkles },
    ]
  },
  {
    id: 'data',
    label: 'Data',
    icon: Database,
    items: [
      { id: 'datasources', label: 'Data Sources & Intake', icon: Database },
      { id: 'models', label: 'ML Models', icon: Cpu },
    ]
  },
  {
    id: 'system',
    label: 'Reports & System',
    icon: Settings,
    items: [
      { id: 'reports', label: 'Official Reports', icon: FileText },
      { id: 'settings', label: 'Settings & Status', icon: Settings },
    ]
  }
];

export const VALID_TABS = [
  'home', 'dashboard', 'monitoring', 'events', 'workspace', 
  'map', 'attribution', 'assistant', 'models', 'datasources', 
  'reports', 'settings'
];

// Helper to extract tab and eventId from URL hash
const parseLocation = () => {
  if (typeof window === 'undefined') return { tab: 'home', eventId: null };
  const raw = window.location.hash.replace(/^#\/?/, '').trim();
  if (!raw) return { tab: 'home', eventId: null };
  const parts = raw.split(/[\/?]/);
  const tabPart = parts[0];
  let eventPart = null;
  if (parts.length > 1 && parts[1]) {
    eventPart = parts[1].replace(/^event=/, '').trim();
  }
  return {
    tab: VALID_TABS.includes(tabPart) ? tabPart : 'home',
    eventId: eventPart || (tabPart === 'workspace' ? 'EVT-0001' : null)
  };
};

export default function App() {
  const initialLoc = parseLocation();
  const [activeTab, setActiveTab] = useState(initialLoc.tab);
  const [selectedEventId, setSelectedEventId] = useState(initialLoc.eventId || 'EVT-0001');
  const [selectedStation, setSelectedStation] = useState('');
  const [selectedRegionId, setSelectedRegionId] = useState('in-mp-indore');
  const [openDropdown, setOpenDropdown] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navRef = useRef(null);
  const selectedRegion = REGIONS_OPTIONS.find(r => r.id === selectedRegionId) || REGIONS_OPTIONS[1];

  // Current active group (parent of the activeTab)
  const activeGroup = NAV_GROUPS.find(g => g.items.some(i => i.id === activeTab)) || NAV_GROUPS[0];

  // Mobile accordion state: default active group expanded
  const [mobileExpandedGroups, setMobileExpandedGroups] = useState({ [activeGroup.id]: true });

  // Keep active group expanded in mobile drawer on activeTab change
  useEffect(() => {
    if (activeGroup) {
      setMobileExpandedGroups(prev => ({ ...prev, [activeGroup.id]: true }));
    }
  }, [activeGroup.id]);

  // Sync state with browser hash navigation (Back / Forward / direct URL)
  useEffect(() => {
    const handleHashChange = () => {
      const { tab, eventId } = parseLocation();
      setActiveTab(tab);
      if (eventId) {
        setSelectedEventId(eventId);
      } else if (tab === 'workspace' && !selectedEventId) {
        setSelectedEventId('EVT-0001');
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [selectedEventId]);

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(event) {
      if (navRef.current && !navRef.current.contains(event.target)) {
        setOpenDropdown(null);
      }
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setOpenDropdown(null);
        setMobileMenuOpen(false);
      }
    }
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const selectTab = (tabId, eventId = null) => {
    if (!VALID_TABS.includes(tabId)) return;
    setActiveTab(tabId);

    let targetEvent = eventId;
    if (tabId === 'workspace') {
      targetEvent = eventId || selectedEventId || 'EVT-0001';
      setSelectedEventId(targetEvent);
    } else if (eventId) {
      setSelectedEventId(eventId);
    }

    const newHash = targetEvent && tabId === 'workspace' ? `#${tabId}/${targetEvent}` : `#${tabId}`;
    if (window.location.hash !== newHash) {
      window.location.hash = newHash;
    }
    setOpenDropdown(null);
    setMobileMenuOpen(false);
  };

  const handleParentClick = (group) => {
    // Clicking any parent navigation item toggles expanding/collapsing its submenu
    setOpenDropdown(prev => prev === group.id ? null : group.id);
  };

  const toggleMobileGroup = (groupId) => {
    setMobileExpandedGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId]
    }));
  };

  const handleNavigateToWorkspace = (eventId) => {
    const targetEvent = eventId || selectedEventId || 'EVT-0001';
    selectTab('workspace', targetEvent);
  };

  const handleNavigateToAssistant = (eventId) => {
    if (eventId) setSelectedEventId(eventId);
    selectTab('assistant');
  };

  const handleNavigateToEvents = (stationName) => {
    if (stationName) setSelectedStation(stationName);
    selectTab('events');
  };

  return (
    <div className="app-container">
      {/* Tier 1: Main Top Navbar */}
      <nav className="navbar" ref={navRef} aria-label="Main Navigation">
        {/* Brand */}
        <button 
          className="brand" 
          onClick={() => selectTab('home')}
          aria-label="AIR KAVACH Homepage"
        >
          <div className="brand-icon-wrapper">
            <Shield size={20} />
          </div>
          <div>
            <span className="brand-title">AIR KAVACH</span>
            <span className="brand-subtitle">Environmental Intelligence</span>
          </div>
        </button>

        {/* Grouped Desktop Navigation */}
        <ul className="nav-groups" role="menubar">
          {NAV_GROUPS.map((group) => {
            const isGroupActive = group.id === activeGroup.id;
            const isOpen = openDropdown === group.id;

            return (
              <li key={group.id} className="nav-group-item" role="none">
                <button
                  className={`nav-group-trigger ${isGroupActive ? 'active' : ''}`}
                  onClick={() => handleParentClick(group)}
                  aria-expanded={isOpen}
                  aria-haspopup="true"
                  role="menuitem"
                  title={`Open ${group.label}`}
                >
                  <group.icon size={15} style={{ color: isGroupActive ? 'var(--primary)' : 'var(--text-secondary)' }} />
                  <span>{group.label}</span>
                  <ChevronDown size={13} style={{ opacity: 0.7, transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
                </button>

                {isOpen && (
                  <div className="nav-dropdown" role="menu">
                    {group.items.map((item) => {
                      const ItemIcon = item.icon;
                      const isActive = activeTab === item.id;
                      return (
                        <button
                          key={item.id}
                          className={`nav-dropdown-item ${isActive ? 'active' : ''}`}
                          onClick={() => selectTab(item.id)}
                          role="menuitem"
                        >
                          <ItemIcon size={14} />
                          <span>{item.label}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        {/* Right Section: Region Selector & Mobile Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <RegionSelector 
            selectedRegion={selectedRegionId} 
            onSelectRegion={setSelectedRegionId} 
          />

          <button 
            className="mobile-nav-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </nav>

      {/* Tier 2: Persistent Subtabs Navigation Bar for Active Group */}
      <div className="subnav-bar" role="navigation" aria-label={`${activeGroup.label} Sub-navigation`}>
        <div className="subnav-container">
          <div className="subnav-group-label">
            <activeGroup.icon size={13} />
            <span>{activeGroup.label}</span>
          </div>

          <div className="subnav-items" role="tablist">
            {activeGroup.items.map((item) => {
              const ItemIcon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  className={`subnav-item ${isActive ? 'active' : ''}`}
                  onClick={() => selectTab(item.id)}
                  role="tab"
                  aria-selected={isActive}
                  title={`Switch to ${item.label}`}
                >
                  <ItemIcon size={14} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Mobile Drawer (Sidebar) Navigation with Accordion Groups */}
      {mobileMenuOpen && (
        <div className="mobile-drawer-overlay" onClick={() => setMobileMenuOpen(false)}>
          <div className="mobile-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-drawer-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <div className="brand-icon-wrapper" style={{ width: '32px', height: '32px' }}>
                  <Shield size={18} />
                </div>
                <strong style={{ color: 'var(--primary)', fontSize: '1.1rem' }}>AIR KAVACH</strong>
              </div>
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="btn-ghost"
                style={{ padding: '0.25rem' }}
                aria-label="Close menu"
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {NAV_GROUPS.map((group) => {
                const isGroupActive = group.id === activeGroup.id;
                const isExpanded = !!mobileExpandedGroups[group.id];

                return (
                  <div key={group.id} className="mobile-nav-group">
                    <button 
                      className={`mobile-nav-group-header ${isGroupActive ? 'active' : ''}`}
                      onClick={() => toggleMobileGroup(group.id)}
                      aria-expanded={isExpanded}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <group.icon size={16} />
                        <span>{group.label}</span>
                      </div>
                      <ChevronDown 
                        size={14} 
                        style={{ 
                          transform: isExpanded ? 'rotate(180deg)' : 'none', 
                          transition: 'transform 0.15s ease' 
                        }} 
                      />
                    </button>

                    {isExpanded && (
                      <div className="mobile-nav-subitems">
                        {group.items.map((item) => {
                          const ItemIcon = item.icon;
                          const isActive = activeTab === item.id;
                          return (
                            <button
                              key={item.id}
                              className={`mobile-nav-item ${isActive ? 'active' : ''}`}
                              onClick={() => selectTab(item.id)}
                            >
                              <ItemIcon size={15} />
                              <span>{item.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Main View Area */}
      <main className="main-content" role="main">
        {activeTab === 'home' && (
          <LandingPage onLaunch={() => selectTab('dashboard')} />
        )}
        {activeTab === 'dashboard' && (
          <MainDashboard 
            region={selectedRegion}
            onNavigateToEvent={handleNavigateToWorkspace}
            onNavigateToEvents={handleNavigateToEvents}
          />
        )}
        {activeTab === 'monitoring' && (
          <MonitoringPage 
            region={selectedRegion} 
            initialStation={selectedStation}
          />
        )}
        {activeTab === 'events' && (
          <PollutionEventsPage 
            region={selectedRegion} 
            initialStation={selectedStation}
            onSelectEvent={handleNavigateToWorkspace} 
          />
        )}
        {activeTab === 'workspace' && (
          <EventWorkspacePage 
            eventId={selectedEventId} 
            region={selectedRegion}
            onBack={() => selectTab('events')} 
            onNavigateToAssistant={handleNavigateToAssistant}
            onSelectEvent={(eid) => selectTab('workspace', eid)}
          />
        )}
        {activeTab === 'map' && (
          <InteractiveMapPage region={selectedRegion} />
        )}
        {activeTab === 'attribution' && (
          <SourceAttributionPage 
            region={selectedRegion}
            onSelectEvent={handleNavigateToWorkspace} 
          />
        )}
        {activeTab === 'assistant' && (
          <AIAssistantPage 
            region={selectedRegion}
            initialEventId={selectedEventId} 
          />
        )}
        {activeTab === 'models' && (
          <ModelMonitoringPage />
        )}
        {activeTab === 'datasources' && (
          <DataSourcesPage region={selectedRegion} />
        )}
        {activeTab === 'reports' && (
          <ReportsPage />
        )}
        {activeTab === 'settings' && (
          <SettingsPage />
        )}
      </main>

      {/* Footer */}
      <footer className="footer" role="contentinfo">
        <div className="footer-content">
          <div>
            <strong>AIR KAVACH (एयर कवच)</strong> — Pan-India Environmental Intelligence & Source Attribution Platform
          </div>
          <div className="footer-text">
            Active Scope: {selectedRegion.name} | CPCB/CAAQMS Telemetry Validation Region
          </div>
        </div>
      </footer>
    </div>
  );
}
