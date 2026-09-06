FROM devkitpro/devkitarm:latest

# Packaging tools are built from reviewed, immutable upstream revisions.
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-bin fontconfig \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/3DSGuy/Project_CTR.git /tmp/ctr \
    && cd /tmp/ctr && git checkout e8f5f529c54ff9b22a2491a480ffa69206bf7b19 \
    && make -C makerom deps -j2 && make -C makerom -j2 \
    && install makerom/bin/makerom /usr/local/bin/makerom
RUN git clone https://github.com/diasurgical/bannertool.git /tmp/bannertool \
    && cd /tmp/bannertool && git checkout 16d8c5a0ce02a5e06e64ab42275132fca57c04a2 \
    && gcc -O2 -c source/pc/stb_image.c source/pc/stb_vorbis.c \
    && g++ -O2 -std=c++11 -DVERSION_MAJOR=1 -DVERSION_MINOR=2 -DVERSION_MICRO=0 \
       source/*.cpp source/3ds/*.cpp source/pc/*.cpp *.o -o /usr/local/bin/bannertool
COPY tools/fonts/Inter-Regular.ttf /usr/local/share/fonts/Inter-Regular.ttf
RUN fc-cache -f
