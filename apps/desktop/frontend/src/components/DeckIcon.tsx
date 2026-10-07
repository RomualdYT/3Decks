import type { LucideIcon } from "lucide-react";
import {
  AppWindow, Bell, Check, ChevronDown, ChevronLeft, ChevronRight, CirclePower, Copy, Eye, FileText, Folder, Gauge,
  Globe2, Grid2X2, Info, Keyboard, Languages, Link2, List, Lock, MessageCircle, Mic, MicOff, Monitor, MoonStar,
  Music2, Pause, Play, Plus, Radio, RefreshCw, Settings, SlidersHorizontal, Sparkles, Square, Star, Terminal, Trash2,
  GripVertical, MoreHorizontal, Pencil, Puzzle, Save, Undo2, Video, Volume1, Volume2, VolumeOff, Wifi, Workflow, X,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  extension: Puzzle,
  app: AppWindow, browser: Globe2, terminal: Terminal, folder: Folder, music: Music2, chat: MessageCircle,
  video: Video, record: Radio, lock: Lock, page: FileText, power: CirclePower, gear: Settings, star: Star,
  mic: Mic, "mic-off": MicOff, "volume-up": Volume2, "volume-down": Volume1, "volume-mute": VolumeOff,
  play: Play, pause: Pause, next: ChevronRight, previous: ChevronLeft, plus: Plus, trash: Trash2, close: X,
  eye: Eye, info: Info, grid: Grid2X2, list: List, language: Languages, sliders: SlidersHorizontal, link: Link2,
  status: Gauge, wifi: Wifi, monitor: Monitor, sparkle: Sparkles, theme: MoonStar, workflow: Workflow,
  globe: Globe2, square: Square, down: ChevronDown, bell: Bell, keyboard: Keyboard,
  copy: Copy, refresh: RefreshCw, grip: GripVertical, more: MoreHorizontal, edit: Pencil, save: Save, undo: Undo2, check: Check,
};

export function DeckIcon({ name, size = 20, className }: { name: string; size?: number; className?: string }) {
  const Icon = ICONS[name] ?? AppWindow;
  return <Icon aria-hidden="true" className={className} size={size} strokeWidth={1.9} />;
}
