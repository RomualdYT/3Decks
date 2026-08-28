import {
  ColorArea,
  ColorField,
  ColorPicker,
  ColorSlider,
  ColorSwatch,
  ColorSwatchPicker,
  Label,
  parseColor,
} from "@heroui/react";

const COLORS = ["#66CB10", "#2AA8FF", "#16B9A6", "#FFB020", "#F05D6C", "#E14BDA", "#64748B", "#1DB954"];

export function ColorControl({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="color-control">
      <span className="field-label">{label}</span>
      <div className="color-control-row">
        <ColorSwatchPicker value={value} onChange={(color) => color && onChange(color.toString("hex"))}>
          {COLORS.map((color) => <ColorSwatchPicker.Item key={color} color={color}><ColorSwatchPicker.Swatch /><ColorSwatchPicker.Indicator /></ColorSwatchPicker.Item>)}
        </ColorSwatchPicker>
        <ColorPicker value={parseColor(value)} onChange={(color) => onChange(color.toString("hex"))}>
          <ColorPicker.Trigger className="custom-color-trigger" aria-label={label}><ColorSwatch color={value} /><span>{value.toUpperCase()}</span></ColorPicker.Trigger>
          <ColorPicker.Popover className="color-popover" placement="bottom end">
            <ColorArea colorSpace="hsb" xChannel="saturation" yChannel="brightness"><ColorArea.Thumb /></ColorArea>
            <ColorSlider colorSpace="hsb" channel="hue"><ColorSlider.Track><ColorSlider.Thumb /></ColorSlider.Track></ColorSlider>
            <ColorField><Label>Hex</Label><ColorField.Group><ColorField.Prefix>#</ColorField.Prefix><ColorField.Input /></ColorField.Group></ColorField>
          </ColorPicker.Popover>
        </ColorPicker>
      </div>
    </div>
  );
}
