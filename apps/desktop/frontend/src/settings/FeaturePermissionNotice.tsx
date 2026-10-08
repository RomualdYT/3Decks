import { Alert, Button } from "@heroui/react";
import { DeckIcon } from "../components/DeckIcon";

interface Props {
  title: string;
  description: string;
  action: string;
  busy: boolean;
  onAction: () => void;
}

export function FeaturePermissionNotice({ title, description, action, busy, onAction }: Props) {
  return <Alert status="warning" className="feature-permission">
    <Alert.Indicator><DeckIcon name="lock" size={18} /></Alert.Indicator>
    <Alert.Content>
      <Alert.Title>{title}</Alert.Title>
      <Alert.Description>{description}</Alert.Description>
    </Alert.Content>
    <Button size="sm" variant="outline" isPending={busy} onPress={onAction}>{action}<DeckIcon name="next" size={14} /></Button>
  </Alert>;
}
