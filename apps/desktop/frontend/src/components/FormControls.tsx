import {
  ComboBox,
  Description,
  Input,
  Header,
  Label,
  ListBox,
  NumberField,
  Select,
  TextField,
} from "@heroui/react";
import { DeckIcon } from "./DeckIcon";

export interface Choice {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  group?: string;
}

interface TextControlProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  description?: string;
  placeholder?: string;
  type?: "text" | "password" | "url";
  autoComplete?: string;
  maxLength?: number;
  isRequired?: boolean;
}

export function TextControl({ label, value, onChange, description, placeholder, type = "text", autoComplete, maxLength, isRequired }: TextControlProps) {
  return (
    <TextField className="ui-field" fullWidth value={value} onChange={onChange} isRequired={isRequired}>
      <Label>{label}</Label>
      <Input type={type} autoComplete={autoComplete} placeholder={placeholder} maxLength={maxLength} />
      {description && <Description>{description}</Description>}
    </TextField>
  );
}

interface SelectControlProps {
  label: string;
  value: string;
  choices: Choice[];
  onChange: (value: string) => void;
  description?: string;
}

export function SelectControl({ label, value, choices, onChange, description }: SelectControlProps) {
  const hasRichChoices = choices.some((choice) => choice.icon || choice.description);
  const groups = Array.from(new Set(choices.map((choice) => choice.group ?? "")));
  const renderChoice = (choice: Choice) => (
    <ListBox.Item id={choice.id} key={choice.id} textValue={choice.label}>
      {choice.icon && <span className="choice-icon"><DeckIcon name={choice.icon} size={18} /></span>}
      <span className="choice-copy"><strong>{choice.label}</strong>{choice.description && <small>{choice.description}</small>}</span>
      <ListBox.ItemIndicator />
    </ListBox.Item>
  );

  return (
    <Select className={`ui-field${hasRichChoices ? " ui-rich-select" : ""}`} fullWidth selectedKey={value} onSelectionChange={(key) => key !== null && onChange(String(key))}>
      <Label>{label}</Label>
      <Select.Trigger>
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      {description && <Description>{description}</Description>}
      <Select.Popover className="ui-popover" maxHeight={360}>
        <ListBox className="ui-choice-list">
          {choices.some((choice) => choice.group) ? groups.map((group) => (
            <ListBox.Section key={group} aria-label={group || label}>
              {group && <Header className="ui-choice-group">{group}</Header>}
              {choices.filter((choice) => (choice.group ?? "") === group).map(renderChoice)}
            </ListBox.Section>
          )) : choices.map(renderChoice)}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}

interface ComboControlProps {
  label: string;
  value: string;
  choices: string[];
  onChange: (value: string) => void;
  description?: string;
  placeholder?: string;
}

export function ComboControl({ label, value, choices, onChange, description, placeholder }: ComboControlProps) {
  const unique = Array.from(new Set(choices)).filter(Boolean);
  return (
    <ComboBox
      className="ui-field"
      fullWidth
      allowsCustomValue
      inputValue={value}
      onInputChange={onChange}
      onSelectionChange={(key) => key !== null && onChange(String(key))}
      menuTrigger="focus"
    >
      <Label>{label}</Label>
      <ComboBox.InputGroup>
        <Input placeholder={placeholder} />
        <ComboBox.Trigger />
      </ComboBox.InputGroup>
      {description && <Description>{description}</Description>}
      <ComboBox.Popover className="ui-popover" maxHeight={360}>
        <ListBox>
          {unique.map((choice) => <ListBox.Item id={choice} key={choice} textValue={choice}><DeckIcon name="app" size={18} /><span>{choice}</span></ListBox.Item>)}
        </ListBox>
      </ComboBox.Popover>
    </ComboBox>
  );
}

interface NumberControlProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

export function NumberControl({ label, value, onChange, min, max, step, description }: NumberControlProps) {
  return (
    <NumberField className="ui-field" fullWidth value={value} onChange={onChange} minValue={min} maxValue={max} step={step}>
      <Label>{label}</Label>
      <NumberField.Group>
        <NumberField.DecrementButton />
        <NumberField.Input />
        <NumberField.IncrementButton />
      </NumberField.Group>
      {description && <Description>{description}</Description>}
    </NumberField>
  );
}
