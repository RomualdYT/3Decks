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
int main(void)
{
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
