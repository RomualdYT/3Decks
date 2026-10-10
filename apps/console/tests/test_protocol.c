#include "app.h"
#include "protocol.h"
#include "json.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static JsonDoc doc;
static Config config, previous;
static PcState state;
static IncomingMessage message;
static bool decode(const char *wire) {
    return protocol_decode(wire, strlen(wire), &message, &config, &state);
}
static void test_pairing_token_roundtrip(void)
{
    /* Matches the desktop's 32 random bytes encoded as 64 hex characters. */
    const char *issued = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    char reply[256], hello[192], sent[128];
    Settings settings = {0};
    assert(strlen(issued) == 64);
    snprintf(reply, sizeof(reply), "{\"type\":\"hello.ok\",\"token\":\"%s\"}", issued);
    assert(decode(reply) && message.kind == MSG_HELLO_OK);
    assert(!strcmp(message.paired_token, issued));
    snprintf(settings.token, sizeof(settings.token), "%s", message.paired_token);
    assert(!strcmp(settings.token, issued));
    int written = protocol_encode_hello(hello, sizeof(hello), "new_3ds_xl", settings.token, "", "en");
    assert(written > 0 && (size_t)written < sizeof(hello));
    assert(json_parse(&doc, hello, (size_t)written));
    assert(json_get_string(&doc, json_root(&doc), "token", sent, sizeof(sent)));
    assert(!strcmp(sent, issued));
    /* Exercise the serializer without depending on decode/storage buffers. */
    written = protocol_encode_hello(hello, sizeof(hello), "new_3ds_xl", issued, "", "en");
    assert(written > 0 && (size_t)written < sizeof(hello));
    assert(json_parse(&doc, hello, (size_t)written));
    assert(json_get_string(&doc, json_root(&doc), "token", sent, sizeof(sent)));
    assert(!strcmp(sent, issued));
    /* A fresh code must still take precedence over a stale stored token. */
    written = protocol_encode_hello(hello, sizeof(hello), "3ds", "stale", "123456", "fr");
    assert(written > 0 && (size_t)written < sizeof(hello));
    assert(json_parse(&doc, hello, (size_t)written));
    assert(json_get_string(&doc, json_root(&doc), "pair_code", sent, sizeof(sent)));
    assert(!strcmp(sent, "123456") && json_get(&doc, json_root(&doc), "token") == NULL);
}
int main(void)
{
    test_pairing_token_roundtrip();
    const char *labels[] = {"Main", "Principal", "Fenêtres", "Musique 🎵"};
    char wire[1024], label[64];
    for (size_t i = 0; i < sizeof(labels)/sizeof(*labels); i++) {
        snprintf(wire, sizeof(wire),
            "{\"type\":\"config.snapshot\",\"revision\":7,\"pages\":[{\"id\":\"main\",\"title\":\"%s\","
            "\"buttons\":[{\"id\":\"play\",\"slot\":5,\"label\":\"Play\"},{\"id\":\"bad\",\"slot\":6}]}]}", labels[i]);
        assert(decode(wire));
        assert(config.revision == 7 && config.page_count == 1);
        assert(!strcmp(config.pages[0].title, labels[i]));
        assert(config.pages[0].buttons[5].used);
    }
    previous = config;
    assert(!decode("{\"type\":\"config.snapshot\",\"pages\":[]}"));
    assert(!memcmp(&previous, &config, sizeof(config)));
    assert(!decode("{\"type\":\"config.snapshot\",\"pages\":["));
    assert(!memcmp(&previous, &config, sizeof(config)));
    assert(decode("{\"type\":\"state.update\",\"extension_panels\":[{\"page\":\"main\",\"title\":\"Custom\",\"cards\":[{\"label\":\"CPU\",\"value\":\"42%\",\"progress\":42}]}]}"));
    assert(state.extension_panel_count == 1 && state.extension_panels[0].cards[0].progress == 42);
    assert(decode("{\"type\":\"state.update\",\"audio_output\":\"USB Headphones\",\"audio_output_mode\":\"direct\",\"audio_output_count\":2,\"audio_output_options\":[{\"id\":\"0123456789abcdef0123456789abcdef\",\"name\":\"USB Headphones\",\"active\":true},{\"id\":\"fedcba9876543210fedcba9876543210\",\"name\":\"Speakers\",\"active\":false}]}"));
    assert(state.audio_output_mode == AUDIO_OUTPUT_DIRECT && state.audio_output_count == 2);
    assert(state.audio_output_total == 2 && state.audio_outputs[0].active);
    assert(!strcmp(state.audio_outputs[1].name, "Speakers"));
    assert(protocol_encode_audio_output_select(wire, sizeof(wire), 17, state.audio_outputs[1].id) > 0);
    assert(!strcmp(wire, "{\"type\":\"audio.output.select\",\"id\":17,\"output\":\"fedcba9876543210fedcba9876543210\"}"));
    assert(decode("{\"type\":\"state.update\",\"audio_output\":\"\",\"audio_output_mode\":\"host_only\",\"audio_output_count\":0,\"audio_output_options\":[]}"));
    assert(state.audio_output_mode == AUDIO_OUTPUT_HOST_ONLY && state.audio_output_count == 0);
    assert(decode("{\"type\":\"state.update\",\"media\":{\"title\":\"Titre\",\"artist\":\"Artiste\",\"position\":12,\"duration\":180,\"seekable\":true}}"));
    assert(state.media_seekable && state.media_position == 12);
    assert(decode("{\"type\":\"media.lyrics\",\"track\":\"Titre\",\"artist\":\"Artiste\",\"status\":\"ready\",\"lines\":[{\"t\":12000,\"text\":\"Première ligne\"},{\"t\":16000,\"text\":\"Deuxième ligne\"}]}"));
    assert(message.kind == MSG_MEDIA_LYRICS && state.lyrics_count == 2);
    assert(state.lyrics[0].time_ms == 12000 && !strcmp(state.lyrics[0].text, "Première ligne"));
    assert(decode("{\"type\":\"media.lyrics\",\"track\":\"Ancien titre\",\"artist\":\"Artiste\",\"status\":\"ready\",\"lines\":[]}"));
    assert(state.lyrics_count == 2);
    assert(decode("{\"type\":\"state.update\",\"media\":{\"title\":\"Autre titre\",\"artist\":\"Artiste\",\"duration\":180}}"));
    assert(state.lyrics_count == 0 && !strcmp(state.lyrics_status, "loading"));
    assert(decode("{\"type\":\"hello.ok\",\"host\":\"Test computer\"}"));
    assert(message.kind == MSG_HELLO_OK);
    assert(decode("{\"type\":\"pong\",\"id\":123}")); assert(message.ping_id == 123);
    assert(decode("{\"type\":\"action.result\",\"id\":9,\"ok\":true,\"open_page\":\"main\"}"));
    assert(message.action_ok && message.action_id == 9 && !strcmp(message.open_page,"main"));
    AgentAnnouncement agent;
    const char *announcement = "{\"type\":\"deck3ds.agent\",\"protocol\":1,\"name\":\"Test computer\",\"port\":9000}";
    assert(protocol_decode_discovery(announcement, strlen(announcement), &agent));
    assert(agent.port == 9000);
    const char *invalid[] = {"01", "1e", "1.", "1+2", "--1", "{\"x\":1,}", "[1,]", "\"\\q\""};
    for (size_t i = 0; i < sizeof(invalid)/sizeof(*invalid); i++)
        assert(!json_parse(&doc, invalid[i], strlen(invalid[i])));
    assert(json_parse(&doc, "1e999", 5));
    assert(json_int(&doc, json_root(&doc), 17) == 17);
    assert(json_float(&doc, json_root(&doc), 17) == 17);
    assert(json_parse(&doc, "\"éé\"", strlen("\"éé\"")));
    char short_label[4];
    assert(json_copy_string(&doc, json_root(&doc), short_label, sizeof(short_label)));
    assert(!strcmp(short_label, "é"));
    assert(json_parse(&doc, "\"\\u00e9\"", 8));
    assert(json_copy_string(&doc, json_root(&doc), label, sizeof(label)) && !strcmp(label, "é"));
    memset(wire, '[', JSON_MAX_DEPTH + 2);
    memset(wire + JSON_MAX_DEPTH + 2, ']', JSON_MAX_DEPTH + 2);
    assert(!json_parse(&doc, wire, 2*(JSON_MAX_DEPTH+2)));
    puts("protocol: FR/EN/UTF-8, snapshots, extensions, discovery, action results and malformed JSON passed");
}
