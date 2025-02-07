import { create } from "zustand";

const useAnalysisStore = create((set) => ({
  userRequestedAnalysisList: [],
  setUserRequestedAnalysisList: (analyses) =>
    set(() => ({
      userRequestedAnalysisList: analyses,
    })),
}));

export default useAnalysisStore;
