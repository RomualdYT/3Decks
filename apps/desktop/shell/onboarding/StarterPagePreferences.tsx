import type { Locale } from "../../frontend/src/app/types";
import { SelectControl } from "../../frontend/src/components/FormControls";

interface Props {
  locale: Locale;
  apps: string[];
  favorites: string[];
  onFavorite: (slot: number, app: string) => void;
  musicView: string;
  onMusicView: (view: string) => void;
  media: boolean;
  lyrics: boolean;
  artwork: boolean;
}

export function StarterPagePreferences({
  locale,
  apps,
  favorites,
  onFavorite,
  musicView,
  onMusicView,
  media,
  lyrics,
  artwork,
}: Props) {
  const fr = locale === "fr";
  return (
    <section className="onboarding-page-preferences">
      <h2>{fr ? "Accueil et Musique" : "Home and Music"}</h2>
      <p>
        {fr
          ? "Accueil, Musique, Applications et Ordinateur. Vous pourrez tout modifier dans l’éditeur."
          : "Home, Music, Applications and Computer. You can customize everything in the editor."}
      </p>
      {apps.length > 0 && (
        <div className="onboarding-favorites">
          {[0, 1].map((slot) => (
            <SelectControl
              key={slot}
              label={
                fr
                  ? `Favori ${slot + 1} sur Accueil`
                  : `Home favorite ${slot + 1}`
              }
              value={favorites[slot] || "__default"}
              choices={[
                {
                  id: "__default",
                  label:
                    slot === 0
                      ? fr
                        ? "Fichiers"
                        : "Files"
                      : fr
                        ? "Verrouiller"
                        : "Lock",
                },
                ...apps
                  .filter((app) => app !== favorites[1 - slot])
                  .map((app) => ({ id: app, label: app })),
              ]}
              onChange={(value) =>
                onFavorite(slot, value === "__default" ? "" : value)
              }
            />
          ))}
        </div>
      )}
      {media && (
        <SelectControl
          label={fr ? "Affichage de Musique" : "Music display"}
          value={musicView}
          choices={[
            { id: "media", label: fr ? "Morceau et pochette" : "Now playing" },
            ...(lyrics
              ? [
                  {
                    id: "lyrics",
                    label: fr ? "Paroles synchronisées" : "Synced lyrics",
                  },
                ]
              : []),
            ...(artwork
              ? [
                  {
                    id: "frame",
                    label: fr ? "Pochette plein écran" : "Full-screen artwork",
                  },
                ]
              : []),
          ]}
          onChange={onMusicView}
        />
      )}
    </section>
  );
}
