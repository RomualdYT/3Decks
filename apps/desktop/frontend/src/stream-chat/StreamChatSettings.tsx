import {
  Alert,
  Button,
  Card,
  Chip,
  Description,
  Label,
  Switch,
} from "@heroui/react";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { TextControl } from "../components/FormControls";
import { StreamChatFeed } from "./StreamChatFeed";
import { useStreamChat } from "./useStreamChat";
import { chatStatus } from "./copy";
import type { StreamChatSettings as Settings } from "./types";
import "./stream-chat.css";

function ReadingOption({
  title,
  description,
  selected,
  disabled,
  onChange,
}: {
  title: string;
  description: string;
  selected: boolean;
  disabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <Switch
      className="stream-chat-option"
      isSelected={selected}
      isDisabled={disabled}
      onChange={onChange}
    >
      <Switch.Content>
        <Label>{title}</Label>
        <Switch.Control>
          <Switch.Thumb />
        </Switch.Control>
      </Switch.Content>
      <Description>{description}</Description>
    </Switch>
  );
}

export function StreamChatSettings({ locale }: { locale: Locale }) {
  const fr = locale === "fr";
  const { view, draft, setDraft, dirty, busy, error, operate } =
    useStreamChat();
  const update = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  const needsAuthorization =
    !view?.account ||
    [
      "authorization_required",
      "authorization_denied",
      "authorization_expired",
    ].includes(view.snapshot.status);
  const failure = error || view?.error;
  const ownChannel = view?.account ?? "";
  const options = [
    {
      key: "compact",
      title: fr ? "Texte compact" : "Compact text",
      description: fr
        ? "Plus de messages visibles à l’écran."
        : "Fit more messages on screen.",
    },
    {
      key: "timestamps",
      title: fr ? "Afficher l’heure" : "Show timestamps",
      description: fr ? "Heure des messages en UTC." : "Message time in UTC.",
    },
    {
      key: "hide_commands",
      title: fr ? "Masquer les commandes" : "Hide commands",
      description: fr
        ? "Masque les messages qui commencent par !."
        : "Hide messages starting with !.",
    },
  ] as const;

  return (
    <div className="settings-content stream-chat-settings">
      <div className="settings-title">
        <span>
          <DeckIcon name="chat" size={24} />
        </span>
        <div>
          <h1>Streaming</h1>
          <p>
            {fr
              ? "Votre chat sur la 3DS, vos commandes OBS à portée de main."
              : "Your chat on the 3DS, with OBS controls within reach."}
          </p>
        </div>
      </div>
      {!window.decksDesktopControls || view?.supported === false ? (
        <Alert status="default">
          <Alert.Content>
            <Alert.Description>
              {chatStatus("unsupported_platform", locale)}
            </Alert.Description>
          </Alert.Content>
        </Alert>
      ) : !view || !draft ? (
        <p role="status">
          {error ? chatStatus(error, locale) : fr ? "Chargement…" : "Loading…"}
        </p>
      ) : (
        <>
          <div className="stream-chat-toolbar">
            <span role="status">
              {dirty
                ? fr
                  ? "Modifications non enregistrées"
                  : "Unsaved changes"
                : chatStatus(view.snapshot.status, locale)}
            </span>
            <Button
              size="sm"
              variant="primary"
              isDisabled={!dirty || busy}
              isPending={busy}
              onPress={() => void operate("save")}
            >
              <DeckIcon name="save" size={15} />
              {fr ? "Enregistrer" : "Save changes"}
            </Button>
          </div>
          {failure && (
            <Alert status="warning">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>
                  {chatStatus(failure, locale)}
                </Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          <Card className="stream-chat-settings-card" variant="secondary">
            <Card.Header className="stream-chat-card-heading">
              <span className="setting-icon">
                <DeckIcon name="chat" />
              </span>
              <div>
                <Card.Title>{fr ? "Chat Twitch" : "Twitch chat"}</Card.Title>
                <Card.Description>
                  {fr
                    ? "Connectez votre compte, puis choisissez le chat à afficher."
                    : "Connect your account, then choose the chat to display."}
                </Card.Description>
              </div>
              <Switch
                aria-label={
                  fr
                    ? "Afficher le chat sur la console"
                    : "Show chat on the console"
                }
                isSelected={draft.enabled}
                isDisabled={busy}
                onChange={(value) => update("enabled", value)}
              >
                <Switch.Content>
                  <Switch.Control>
                    <Switch.Thumb />
                  </Switch.Control>
                </Switch.Content>
              </Switch>
            </Card.Header>
            <Card.Content className="stream-chat-card-body">
              <div className="stream-chat-account">
                <span className="stream-chat-account-icon">
                  <DeckIcon
                    name={ownChannel && !needsAuthorization ? "check" : "lock"}
                    size={19}
                  />
                </span>
                <div className="stream-chat-account-copy">
                  <strong>
                    {ownChannel
                      ? `@${ownChannel}`
                      : fr
                        ? "Votre compte Twitch"
                        : "Your Twitch account"}
                  </strong>
                  <p>
                    {view.authorization
                      ? fr
                        ? "Confirmez la connexion dans votre navigateur."
                        : "Confirm the connection in your browser."
                      : ownChannel && !needsAuthorization
                        ? fr
                          ? "Compte connecté · lecture du chat uniquement"
                          : "Account connected · read chat only"
                        : fr
                          ? "Une autorisation Twitch est nécessaire pour lire les messages."
                          : "Twitch authorization is required to read messages."}
                  </p>
                </div>
                <div className="stream-chat-actions">
                  {ownChannel && !needsAuthorization && !view.authorization && (
                    <Chip color="success" variant="secondary" size="sm">
                      <Chip.Label>{fr ? "Autorisé" : "Authorized"}</Chip.Label>
                    </Chip>
                  )}
                  {needsAuthorization && !view.authorization && (
                    <Button
                      variant="primary"
                      isDisabled={busy}
                      isPending={busy}
                      onPress={() => void operate("authorize")}
                    >
                      <DeckIcon name="link" size={16} />
                      {ownChannel
                        ? fr
                          ? "Reconnecter"
                          : "Reconnect"
                        : fr
                          ? "Connecter Twitch"
                          : "Connect Twitch"}
                    </Button>
                  )}
                  {(ownChannel || view.authorization) && (
                    <Button
                      size="sm"
                      variant="ghost"
                      isDisabled={busy}
                      onPress={() => void operate("disconnect")}
                    >
                      {view.authorization
                        ? fr
                          ? "Annuler"
                          : "Cancel"
                        : fr
                          ? "Déconnecter"
                          : "Disconnect"}
                    </Button>
                  )}
                </div>
              </div>
              {view.authorization && (
                <Alert status="accent" className="stream-chat-authorization">
                  <Alert.Indicator>
                    <DeckIcon name="link" size={20} />
                  </Alert.Indicator>
                  <Alert.Content>
                    <Alert.Title>
                      {fr
                        ? "Confirmez ce code sur Twitch"
                        : "Confirm this code on Twitch"}
                    </Alert.Title>
                    <Alert.Description>
                      {fr
                        ? "La page Twitch s’ouvre dans votre navigateur. La connexion se termine automatiquement après votre autorisation."
                        : "Twitch opens in your browser. Connection finishes automatically after you authorize it."}
                    </Alert.Description>
                    <code>{view.authorization.code}</code>
                    <Button
                      size="sm"
                      variant="outline"
                      isDisabled={busy}
                      onPress={() => void operate("open")}
                    >
                      {fr ? "Ouvrir Twitch" : "Open Twitch"}
                      <DeckIcon name="link" size={14} />
                    </Button>
                  </Alert.Content>
                </Alert>
              )}
              <div className="stream-chat-channel">
                <TextControl
                  label={fr ? "Chaîne du chat" : "Chat channel"}
                  value={draft.channel}
                  onChange={(value) => update("channel", value)}
                  placeholder={ownChannel || "twitch.tv/your_channel"}
                  maxLength={200}
                  autoComplete="off"
                  isDisabled={busy}
                  description={
                    fr
                      ? "Nom, @pseudo ou lien Twitch. Votre chaîne ou celle d’un autre streamer."
                      : "Channel name, @username or Twitch link. Your channel or another streamer’s."
                  }
                />
                {ownChannel &&
                  draft.channel.toLowerCase() !== ownChannel.toLowerCase() && (
                    <Button
                      size="sm"
                      variant="ghost"
                      isDisabled={busy}
                      onPress={() => update("channel", ownChannel)}
                    >
                      <DeckIcon name="undo" size={14} />
                      {fr ? "Utiliser ma chaîne" : "Use my channel"}
                    </Button>
                  )}
                {!ownChannel && !draft.channel && (
                  <p className="stream-chat-channel-hint">
                    {fr
                      ? "Votre propre chaîne sera sélectionnée après la connexion. Vous pourrez en choisir une autre."
                      : "Your own channel is selected after connecting. You can choose another one."}
                  </p>
                )}
              </div>
            </Card.Content>
            <Card.Footer className="stream-chat-card-note">
              <DeckIcon name="lock" size={14} />
              <span>
                {fr
                  ? "Lecture seule. 3Decks ne publie aucun message dans le chat."
                  : "Read only. 3Decks never posts messages to chat."}
              </span>
            </Card.Footer>
          </Card>

          <Card className="stream-chat-settings-card" variant="secondary">
            <Card.Header>
              <Card.Title>
                {fr ? "Affichage sur la console" : "Console display"}
              </Card.Title>
              <Card.Description>
                {fr
                  ? "Adaptez la lecture au petit écran de la 3DS."
                  : "Adjust reading for the 3DS’s small screen."}
              </Card.Description>
            </Card.Header>
            <Card.Content className="stream-chat-options">
              {options.map(({ key, title, description }) => (
                <ReadingOption
                  key={key}
                  title={title}
                  description={description}
                  selected={draft[key]}
                  disabled={busy}
                  onChange={(value) => update(key, value)}
                />
              ))}
            </Card.Content>
          </Card>

          {draft.client_id && (
            <Alert status="warning">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Title>
                  {fr
                    ? "Configuration Twitch personnalisée"
                    : "Custom Twitch configuration"}
                </Alert.Title>
                <Alert.Description>
                  {fr
                    ? "Cette installation utilise un autre identifiant d’application. Rétablissez celui de 3Decks, enregistrez puis reconnectez votre compte."
                    : "This installation uses a different application ID. Restore the 3Decks default, save, then reconnect your account."}
                </Alert.Description>
              </Alert.Content>
              <Button
                size="sm"
                variant="outline"
                isDisabled={busy}
                onPress={() => update("client_id", "")}
              >
                {fr ? "Rétablir 3Decks" : "Restore 3Decks"}
              </Button>
            </Alert>
          )}

          <section className="stream-chat-preview">
            <div>
              <h2>{fr ? "Aperçu du chat" : "Chat preview"}</h2>
              <p>
                {fr
                  ? "Dans l’éditeur, choisissez « Chat de stream » pour l’écran supérieur d’une page, ou ajoutez le modèle Streaming."
                  : "In the editor, choose “Stream chat” for a page’s top screen, or add the Streaming template."}
              </p>
            </div>
            <StreamChatFeed snapshot={view.snapshot} locale={locale} />
          </section>
        </>
      )}
    </div>
  );
}
