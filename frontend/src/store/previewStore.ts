import { create } from "zustand"

export type GeneratedFiles = Record<string, string>
export type ViewMode = "preview" | "code"
export type BuildStatus = "idle" | "building" | "ready" | "error"

interface PreviewState {
  files: GeneratedFiles
  selectedFile: string
  view: ViewMode
  previewHtml: string
  buildStatus: BuildStatus
  buildError: string
  lastPrompt: string
  setFiles: (files: GeneratedFiles, prompt: string) => void
  updateFile: (path: string, content: string) => void
  setSelectedFile: (path: string) => void
  setView: (view: ViewMode) => void
  setPreviewHtml: (html: string) => void
  setBuildStatus: (status: BuildStatus) => void
  setBuildError: (error: string) => void
}

const DEFAULT_SELECTED_FILE = "src/App.jsx"

export const usePreviewStore = create<PreviewState>((set) => ({
  files: {},
  selectedFile: DEFAULT_SELECTED_FILE,
  view: "preview",
  previewHtml: "",
  buildStatus: "idle",
  buildError: "",
  lastPrompt: "",
  setFiles: (files: GeneratedFiles, prompt: string) =>
    set(() => {
      const fileNames = Object.keys(files)
      const nextSelectedFile = fileNames.includes(DEFAULT_SELECTED_FILE)
        ? DEFAULT_SELECTED_FILE
        : fileNames[0] || DEFAULT_SELECTED_FILE

      return {
        files,
        selectedFile: nextSelectedFile,
        lastPrompt: prompt,
        buildError: "",
      }
    }),
  updateFile: (path: string, content: string) =>
    set((state: PreviewState) => ({
      files: {
        ...state.files,
        [path]: content,
      },
    })),
  setSelectedFile: (path: string) => set({ selectedFile: path }),
  setView: (view: ViewMode) => set({ view }),
  setPreviewHtml: (html: string) => set({ previewHtml: html }),
  setBuildStatus: (status: BuildStatus) => set({ buildStatus: status }),
  setBuildError: (error: string) => set({ buildError: error }),
}))
