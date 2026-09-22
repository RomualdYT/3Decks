import { describe, expect, it } from "vitest";
import { formatDeviceName } from "./devices";

describe("device name formatter", () => {
  it("translates known console model identifiers to official friendly names", () => {
    expect(formatDeviceName("new_3ds_xl")).toBe("New Nintendo 3DS XL");
    expect(formatDeviceName("new_3ds")).toBe("New Nintendo 3DS");
    expect(formatDeviceName("3ds_xl")).toBe("Nintendo 3DS XL");
    expect(formatDeviceName("3ds")).toBe("Nintendo 3DS");
    expect(formatDeviceName("2ds")).toBe("Nintendo 2DS");
    expect(formatDeviceName("new_2ds_xl")).toBe("New Nintendo 2DS XL");
    expect(formatDeviceName("new3dsxl")).toBe("New Nintendo 3DS XL");
  });

  it("handles case-insensitivity and whitespace", () => {
    expect(formatDeviceName("  NEW_3DS_XL  ")).toBe("New Nintendo 3DS XL");
    expect(formatDeviceName("2DS")).toBe("Nintendo 2DS");
  });

  it("preserves custom user console names as-is", () => {
    expect(formatDeviceName("Console salon")).toBe("Console salon");
    expect(formatDeviceName("Ma Super 3DS")).toBe("Ma Super 3DS");
  });

  it("provides a safe default when name is empty or undefined", () => {
    expect(formatDeviceName(undefined)).toBe("Nintendo 3DS");
    expect(formatDeviceName("")).toBe("Nintendo 3DS");
    expect(formatDeviceName("   ")).toBe("Nintendo 3DS");
  });
});
