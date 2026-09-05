#include "app_network.h"
#include "network_policy.h"
#include "support.h"
#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static App app;
static char output[NET_MAX_MESSAGE + 1];
static unsigned char wire[NET_MAX_MESSAGE + 4];

static int open_listener(int *port)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    assert(fd >= 0);
    struct sockaddr_in address = {0};
    address.sin_family = AF_INET;
    assert(inet_pton(AF_INET, "127.0.0.1", &address.sin_addr) == 1);
    assert(bind(fd, (struct sockaddr *)&address, sizeof(address)) == 0);
    assert(listen(fd, 4) == 0);
    socklen_t size = sizeof(address);
    assert(getsockname(fd, (struct sockaddr *)&address, &size) == 0);
    *port = ntohs(address.sin_port);
    assert(fcntl(fd, F_SETFL, O_NONBLOCK) == 0);
    return fd;
}
static int connect_peer(int listener, int port)
{
    assert(net_connect("127.0.0.1", port));
    int peer = -1;
    for (int i = 0; i < 10000; i++) {
        net_poll();
        if (peer < 0) peer = accept(listener, NULL, NULL);
        if (peer >= 0 && net_state() == NET_CONNECTED) break;
    }
    assert(peer >= 0 && net_state() == NET_CONNECTED);
    return peer;
}
static void send_payload(int peer, const char *payload, size_t size)
{
    wire[0] = size >> 24; wire[1] = size >> 16; wire[2] = size >> 8; wire[3] = size;
    memcpy(wire + 4, payload, size);
    size_t offset = 0;
    while (offset < size + 4) {
        ssize_t written = send(peer, wire + offset, size + 4 - offset, 0);
        assert(written > 0);
        offset += written;
    }
}
static void pump_until_handshake(void)
{
    for (int i = 0; i < 10000 && !app.handshake_ok; i++) app_pump_network(&app);
    assert(app.handshake_ok);
}
int main(void)
{
    alarm(20); /* A transport regression must fail, not hang the CI runner. */
    assert(!deadline_reached(7.9, 8) && deadline_reached(8, 8));
    const double expected[] = {2,4,8,15,30,30};
    for (int i = 0; i < 6; i++) assert(network_retry_delay(i) == expected[i]);
    assert(net_init());
    assert(!net_connect(NULL, 9000) && !net_connect("127.0.0.1", 65536));
    assert(!net_connect("not-an-ip.invalid", 9000) && net_state() == NET_IDLE);
    int port, listener = open_listener(&port);
    assert(net_connect("127.0.0.1", port));
    if (net_state() == NET_CONNECTING) {
        test_now += CONNECT_TIMEOUT_SECONDS;
        net_poll();
        assert(net_state() == NET_IDLE);
    }
    net_disconnect();
    int expired_peer = accept(listener, NULL, NULL);
    if (expired_peer >= 0) close(expired_peer);
    int peer = connect_peer(listener, port);
    memset(output, 'x', NET_MAX_MESSAGE);
    send_payload(peer, output, NET_MAX_MESSAGE);
    /* Valid messages behind a maximum-sized frame must survive extraction. */
    send_payload(peer, "abc", 3);
    size_t size = 0;
    for (int i = 0; i < 10000 && size == 0; i++) {
        net_poll();
        if (net_receive(output, sizeof(output), &size)) break;
    }
    assert(size == NET_MAX_MESSAGE && net_state() == NET_CONNECTED);
    size = 0;
    for (int i = 0; i < 10000 && size == 0; i++) {
        net_poll(); net_receive(output, sizeof(output), &size);
    }
    assert(size == 3 && !strcmp(output, "abc"));
    send_payload(peer, "abc", 3);
    for (int i = 0; i < 10000 && net_state() != NET_IDLE; i++) {
        net_poll(); net_receive(output, 3, &size);
    }
    assert(net_state() == NET_IDLE); close(peer);

    peer = connect_peer(listener, port);
    app.link = LINK_CONNECTING;
    app_pump_network(&app); assert(app.hello_sent);
    /* Animation uptime stays unchanged: real elapsed time must still expire. */
    test_now += HELLO_TIMEOUT_SECONDS;
    app_pump_network(&app);
    assert(net_state() == NET_IDLE && !app.handshake_ok && app.reconnect_in == 2);
    close(peer);

    peer = connect_peer(listener, port);
    app.hello_sent = false; app_pump_network(&app);
    const char *hello = "{\"type\":\"hello.ok\",\"host\":\"Test computer\"}";
    send_payload(peer, hello, strlen(hello)); pump_until_handshake();
    test_now += HEARTBEAT_INTERVAL_SECONDS;
    app_pump_network(&app); assert(app.pending_ping_id >= 0);
    char pong[64]; snprintf(pong, sizeof(pong), "{\"type\":\"pong\",\"id\":%d}", app.pending_ping_id);
    send_payload(peer, pong, strlen(pong));
    for (int i = 0; i < 10000 && app.pending_ping_id >= 0; i++) app_pump_network(&app);
    assert(app.pending_ping_id == -1);
    test_now += HEARTBEAT_TIMEOUT_SECONDS;
    app_pump_network(&app);
    assert(net_state() == NET_IDLE && !app.handshake_ok && app.uptime == 0);
    close(peer);
    strcpy(app.settings.host, "127.0.0.1"); app.settings.port = port;
    app_network_update(&app); assert(net_state() == NET_IDLE);
    test_now = app.reconnect_at;
    app_network_update(&app); assert(net_state() != NET_IDLE);
    app_force_reconnect(&app);
    assert(net_state() == NET_IDLE && app.reconnect_attempt == 0 && app.reconnect_at == test_now);
    close(listener); net_exit();
    puts("network: real loopback framing, hello deadline, heartbeat/pong, backoff and forced reconnect passed");
}
