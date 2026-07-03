import type { PaletteColor } from "@/lib/types";

export default function PaletteSwatch({ color }: { color: PaletteColor }) {
  return (
    <div className="flex flex-col items-center">
      <div
        className="h-14 w-14 rounded-[5px] border border-black/10 shadow-sm"
        style={{ background: color.hex_code }}
      />
      <div className="mt-1 text-center font-mono text-[0.65rem] text-secondary">
        {color.hex_code}
        <br />
        {(color.name ?? "").slice(0, 14)}
      </div>
    </div>
  );
}
