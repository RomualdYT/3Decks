import { Switch } from "@heroui/react";
import type { ActionArgument, Locale } from "../app/types";
import {
  NumberControl,
  SelectControl,
  TextControl,
} from "../components/FormControls";
import { localized } from "../utils/config";

export function ExtensionField({
  field,
  value,
  locale,
  secretSet,
  onChange,
}: {
  field: ActionArgument;
  value: unknown;
  locale: Locale;
  secretSet?: boolean;
  onChange: (value: string | number | boolean) => void;
}) {
  const label = localized(field.label, locale) || field.name;
  const description = localized(field.description, locale);
  if (field.type === "boolean")
    return (
      <div className="extension-switch">
        <div>
          <strong>{label}</strong>
          <p>{description}</p>
        </div>
        <Switch
          aria-label={label}
          isSelected={value === true}
          onChange={onChange}
        >
          <Switch.Content>
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Content>
        </Switch>
      </div>
    );
  if (field.type === "number")
    return (
      <NumberControl
        label={label}
        value={Number(value ?? field.default ?? field.min ?? 0)}
        min={field.min}
        max={field.max}
        description={description}
        onChange={onChange}
      />
    );
  if (field.type === "select")
    return (
      <SelectControl
        label={label}
        value={String(value ?? field.default ?? "")}
        choices={(field.choices ?? []).map((choice) => ({
          id: choice.value,
          label: localized(choice.label, locale),
        }))}
        description={description}
        onChange={onChange}
      />
    );
  return (
    <TextControl
      label={label}
      value={String(value ?? "")}
      type={field.type === "password" ? "password" : "text"}
      maxLength={2048}
      isRequired={field.required && !secretSet}
      autoComplete="off"
      placeholder={
        secretSet
          ? locale === "fr"
            ? "Secret enregistré — laissez vide pour le conserver"
            : "Secret saved — leave unchanged to keep it"
          : undefined
      }
      description={description}
      onChange={onChange}
    />
  );
}
