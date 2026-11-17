# syntax=docker/dockerfile:1
# Ảnh API (Spring Boot): build bằng Maven + JDK 25, chạy bằng JRE 25 trên Alpine dưới người dùng không phải root.
# Build từ thư mục webapp: docker compose build api

FROM maven:3.9-eclipse-temurin-25 AS build
WORKDIR /src
COPY pom.xml ./
RUN --mount=type=cache,target=/root/.m2 mvn -q -B dependency:go-offline
COPY src ./src
# Bộ test (gồm cả PostgreSQL nhúng) chạy trên máy dev / CI trước khi build ảnh, không chạy lại ở đây.
RUN --mount=type=cache,target=/root/.m2 mvn -q -B -DskipTests package \
    && cp target/*.jar /app.jar

FROM eclipse-temurin:25-jre-alpine
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=build --chown=app:app /app.jar ./app.jar
USER app
# Bộ nhớ: heap theo % giới hạn RAM của container (docker-compose đặt), SerialGC tốn ít RAM nhất cho 1–2 CPU.
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=55 -XX:InitialRAMPercentage=15 -XX:+UseSerialGC -XX:MaxMetaspaceSize=192m -XX:ReservedCodeCacheSize=64m -Xss512k -XX:+ExitOnOutOfMemoryError -Duser.timezone=Asia/Ho_Chi_Minh" \
    SPRING_PROFILES_ACTIVE=postgres \
    APP_DATA_DIR=/data/serving \
    APP_ENV_FILE=/app/khong-dung.env
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
