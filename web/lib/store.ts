import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Types
export interface FilterState {
  selectedPlayers: string[];
  selectedPositions: string[];
  dateRange: { from: Date; to: Date } | null;
  sessionType: string | null;
  microcycle: number | null;
}

export interface UserState {
  teamId: string | null;
  email: string | null;
  isLoading: boolean;
}

export interface AppStore {
  // User state
  user: UserState;
  setUser: (user: Partial<UserState>) => void;
  clearUser: () => void;

  // Filters
  filters: FilterState;
  setFilters: (filters: Partial<FilterState>) => void;
  clearFilters: () => void;

  // UI state
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  
  // Selected player for quick view
  selectedPlayerId: string | null;
  setSelectedPlayerId: (id: string | null) => void;
}

const initialUserState: UserState = {
  teamId: null,
  email: null,
  isLoading: false,
};

const initialFilterState: FilterState = {
  selectedPlayers: [],
  selectedPositions: [],
  dateRange: null,
  sessionType: null,
  microcycle: null,
};

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      // User
      user: initialUserState,
      setUser: (user) =>
        set((state) => ({
          user: { ...state.user, ...user },
        })),
      clearUser: () => set({ user: initialUserState }),

      // Filters
      filters: initialFilterState,
      setFilters: (filters) =>
        set((state) => ({
          filters: { ...state.filters, ...filters },
        })),
      clearFilters: () => set({ filters: initialFilterState }),

      // UI
      sidebarOpen: true,
      toggleSidebar: () =>
        set((state) => ({
          sidebarOpen: !state.sidebarOpen,
        })),

      // Player selection
      selectedPlayerId: null,
      setSelectedPlayerId: (id) => set({ selectedPlayerId: id }),
    }),
    {
      name: 'ulisses-store',

    }
  )
);
