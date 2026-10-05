# Mac mini 배포와 운영

2026-10-06: **Mac 내부 검증과 Cloudflare Worker/VPC 게시 완료. 소유자가 운영 사이트 로그인 후 기존 문제 목록 표시를 확인했다.**
운영 주소는 `https://code-trainer.yelihi19.workers.dev`다. 사용자가 생성한 전용 Access 앱의 AUD를 서버에 반영했다. 비로그인 루트 요청이 해당 AUD의 Access 로그인으로 이동하는 것을 확인했다. 기존 resume-agent는 변경하지 않았다.

## 실제 구성

```text
브라우저 → Cloudflare Access → Worker/정적 화면 → VPC Service
                                               ↓ 기존 Tunnel
Mac 127.0.0.1:8010 → 앱 VM: FastAPI, SQLite
앱 VM → https://192.168.5.2:18443 → Mac loopback SSH 전달
                                   ↓ mTLS (앱에서 runner까지)
                         실행 VM 127.0.0.1:8443 → 실행 컨테이너
```

- 앱 VM과 실행 VM은 각각 2GiB/2vCPU이며 서로 다른 Docker 엔진을 사용한다. 앱 이미지에는 Docker CLI/소켓이 없다.
- 앱 VM의 Colima home은 `/Volumes/Storage2TB/server/code-trainer/vm`, 실행 VM은 `.../rvm`이다. 같은 userspace network를 공유하지 않는다.
- 실행 VM은 VZ NAT/bridge NIC·호스트 폴더 공유·SSH agent 전달이 없다. 자체 Docker 소켓은 실행 브로커에만 제공한다.
- 실행 VM과 그 네트워크 프로세스는 Mac의 `sandbox-exec` 정책을 상속한다. IP 외부 연결은 차단하며, 예외는 동일 VM으로 되돌아가는 관리 SSH `localhost:56222`뿐이다. 파일시스템 전체를 sandbox-exec로 제한하는 구성은 아니다.
- `runner-lima-override.yaml`이 자동 TCP/UDP 포트 전달을 끈다. Colima 0.10.3의 `--port-forwarder none`만으로는 Lima 2.2.0에서 loopback 포트 전달을 모두 막지 못해 실제 검사 후 보완했다.
- 호스트의 `127.0.0.1:18443` 전달은 별도 SSH 프로세스가 담당한다. 앱은 서버 인증서를 검증하고 브로커는 별도 CA가 발급한 앱 인증서를 요구한다. 관리 SSH 키는 Mac에만 있다.
- 제출 코드 컨테이너는 non-root, network none, read-only, cap drop, no-new-privileges, 메모리 256MiB, CPU 1, PID 64, 동시 실행 1개를 유지한다.
- 초기 사용자는 **명시적으로 연결된 소유자 1명**이다. backend가 Access 서명·issuer·AUD·만료·subject·email을 검증한다. 앱 설정 누락 시 로컬 로그인으로 우회하지 않는다.
- 기존 resume-agent에서 동일 이메일로 검증되어 저장된 Access subject를 동일 조직의 소유자 신원으로 사용했다. Code Trainer의 기존 사용자 ID와 학습 데이터는 유지한다. 별도 앱의 AUD를 반영했고, 소유자가 실제 로그인 후 기존 문제 목록이 표시됨을 확인했다.

## 경로와 기동

| 용도 | 위치 |
| --- | --- |
| 운영 저장소 | `/Volumes/Storage2TB/server/code-trainer` |
| 앱 VM | 위 경로의 `vm` |
| 실행 VM | 위 경로의 `rvm` |
| 앱 SQLite | 앱 VM의 `code-trainer-data` named volume |
| 실행 이미지 사본 | 위 경로의 `images` |
| runtime 승인 목록 | 위 경로의 `runtime-manifest/runtimes.json` |
| 설정·키 | `~/.config/code-trainer` (0700, 비밀 파일 0600) |
| 호스트 기동 코드 | `~/.config/code-trainer/deployment` |
| macOS 실행 앱 | `~/Applications/Code Trainer Service.app` |
| 암호화 백업 | `~/Library/Application Support/code-trainer-backup/restic` |

`host.py`가 실제 SSD UUID·마운트 지점·표시 파일을 확인한 뒤 작업한다. 실행 VM의 네트워크 정책과 override를 배포 코드와 함께 보관한다. **운영 실행 VM을 일반 `colima start`로 실행하지 않는다.** 반드시 설치된 LaunchAgent 또는 `host.py runner`를 사용한다. 정책 없이 이미 실행된 VM을 나중에 sandbox-exec로 감쌀 수는 없다.

설치된 LaunchAgent:

- `com.code-trainer.app`: 앱 VM foreground 실행.
- `com.code-trainer.runner`: 호스트 네트워크 정책 아래 실행 VM foreground 실행.
- `com.code-trainer.forward`: mTLS용 loopback SSH 전달. VM이 준비되기 전 실패하면 재시도한다.
- `com.code-trainer.backup`: 매일 04:30 일관된 DB 사본과 암호화 백업. resume-agent의 04:00 백업과 시간을 분리했다.

사용자 로그인 후 기동하는 LaunchAgent다. **Mac 전체 재부팅·로그아웃 후 복구는 아직 시험하지 않았다.** 실제 LaunchAgent에서 외장 볼륨 접근과 두 VM의 정지 후 재기동은 확인했다. 설치된 기동 코드는 저장소 편집만으로 바뀌지 않으므로 검증 후 별도로 복사해야 한다.

```sh
launchctl list | rg 'com.code-trainer'
curl --fail http://127.0.0.1:8010/healthz
.venv/bin/python deploy/check-host.py
```

`check-host.py`는 실제 다섯 언어 채점, 앱의 Docker 부재, mTLS 무인증 거부, 실행 VM root의 Mac/앱 네트워크/인터넷 연결 거부, 호스트 공유·두 번째 NIC 부재, 자동 runner 포트 전달 부재와 resume-agent health를 검사한다. 유료 AI 호출은 하지 않는다.

## Cloudflare 게시 상태와 남은 검증

- Access: 사용자 화면에서 `Owner only` Allow 정책과 소유자 이메일, 운영 hostname 연결을 확인했다. 전달받은 전용 AUD는 `~/.config/code-trainer/server.env`에 적용하고 앱 컨테이너를 재생성했다.
- VPC Service: `code-trainer-api`, ID `01a10c90-5876-7e83-b4f0-5ac84a06bfa6`. 기존 Tunnel을 경유해 Mac `127.0.0.1:8010`에 연결한다. 8443/18443은 Cloudflare에 연결하지 않는다.
- Worker: `code-trainer`, 게시 버전 `00c9efaf-f084-4b82-b009-d002dd88ab38`. 운영 PUBLIC_ORIGIN과 `CODE_TRAINER_API` binding을 설정했다. workers.dev는 활성화하고 preview URL은 비활성화했다.
- 운영 설정: `~/.config/code-trainer/deployment/wrangler.production.json`. 저장소의 `wrangler.jsonc`는 배포되지 않는 기본값을 유지한다. 운영 설정의 소스/빌드 경로는 이 Mac의 절대 경로다.
- 확인: 프런트 빌드, 운영 Wrangler dry-run/게시, Cloudflare API의 binding/주소 활성 상태, 비로그인 루트 요청의 Access 리다이렉트 및 AUD 일치, AUD 반영 후 `check-host.py` 통과.
- 사용자 확인(2026-10-06): 운영 사이트에서 로그인 후 기존 문제 목록이 표시된다. 이 결과로 소유자 신원 연결과 목록 조회에 사용하는 Worker → VPC → Mac API 경로의 동작을 확인했다. 에이전트가 직접 브라우저로 검증한 결과는 아니다.
- 미확인: 외부 API/정적 파일 전체의 인증 경계, 문제 상세 조회·채점·AI 생성·로그아웃. 로컬 인증 테스트 성공만으로 외부 검증을 대체하지 않는다.

CLI의 Access 앱 생성 권한이 없어 사용자가 앱을 직접 생성했다. 자동 승인 검토가 대시보드와 운영 사이트의 브라우저 접근을 사용자 설정에 따라 거부했으므로 브라우저 로그인 검증은 사용자에게 요청했다. GitHub CI/CD 구성은 아래와 같으며 실제 첫 실행 결과는 운영 확인 후 기록한다.

운영 설정을 재사용해 화면을 갱신할 때는 프런트 검사/빌드 후 아래 명령을 사용한다. 게시 전 VPC 목적지와 Access 보호가 유지되는지 확인한다.

```sh
node deploy/cloudflare/node_modules/wrangler/bin/wrangler.js deploy \
  --config "$HOME/.config/code-trainer/deployment/wrangler.production.json"
```

## 백업과 복원

`host.py backup`은 SQLite backup API와 무결성 검사로 앱 컨테이너 안에서 사본을 만든 뒤 stdout 스트림으로 Mac의 0700 staging 폴더에 전달한다. 이 Docker 환경에서 `docker cp`는 tmpfs의 생성 파일을 찾지 못해 사용하지 않는다. 사본은 0600이다. restic 성공 후 해당 작업의 staging만 제거한다.

백업에는 DB, 보존한 이미지 archive, runtime 승인 목록, 서버/Compose 설정, 활성 TLS/CA, SSD UUID와 설치된 배포 코드/설정이 포함된다. 서버 설정의 AI 키도 restic으로 암호화된다. restic 암호 자체는 `~/.config/code-trainer/restic-password`에 별도로 둔다. 일별 7개·주별 4개·월별 3개를 보존하며 백업 디스크 여유가 5GiB 미만이면 실패한다. 이 기준은 최대 용량 예약이나 모든 디스크 공간 문제의 방지를 보장하지 않는다.

```sh
python3 ~/.config/code-trainer/deployment/host.py backup
restic --repo "$HOME/Library/Application Support/code-trainer-backup/restic" \
  --password-file "$HOME/.config/code-trainer/restic-password" snapshots
```

첫 스냅샷을 `restic check --read-data`로 검사하고 별도 위치에 DB를 복원해 계정 1개·문제 세트 8개와 SQLite 무결성을 확인했다. 이후 실제 LaunchAgent 백업도 성공했다. **장치 밖에 보관하는 restic 암호/복구 사본은 아직 준비하지 않았다.** 내장 백업은 외장 SSD 고장에 대비하지만 Mac 전체 손실을 막지 못한다.

기존 문제의 runtime ID는 그대로 보존했다. `images/runtime-6a7cf789727c.tar`를 실행 VM으로 가져왔으며 새 빌드 ID로 바꾸지 않았다. 이미지 archive도 암호화 백업 대상이다. 복원할 때는 검증한 새 빈 named volume에 가져온 뒤 Compose 참조를 전환한다. 기존 데이터 볼륨을 덮어쓰지 않는다.

## 배포 이미지와 검증 범위

앱/브로커 이미지 빌드를 실제 arm64 Docker 29.5.2에서 확인했다. Python·Docker CLI 베이스는 digest로 고정했다. Compose의 이미지 값도 `sha256:...`로 지정하며 개인 설정의 `compose.env`에 보관한다. Linux 배포판의 오래된 Docker CLI 대신 Docker 29 CLI를 사용한다.

업데이트는 이미지 준비 → 작업 중단 → 기존 이미지로 일관된 백업 → immutable 이미지 교체 → health/인증/채점 검사 → 같은 SHA의 Worker 게시 순서다. DB 변경 뒤 이전 코드만 자동 롤백하지 않는다.

검증 완료: Python 42개 검사, 프런트 테스트/타입/lint/빌드, Worker 테스트와 dry-run, 두 Linux 이미지 빌드, 실제 Docker 다섯 언어·메모리/시간/출력/PID/파일/네트워크 제한과 정리, 실제 mTLS, VM 네트워크 차단, LaunchAgent 기동, restic 백업·복원.

남은 검증: 운영 사이트의 채점·AI 생성·로그아웃, 외부 모바일망 접속, 전체 Mac 재부팅, 두 앱 최대 작업 부하, 장치 밖 복구, GitHub CI/CD. TLS leaf 인증서는 발급일부터 90일이며 만료 전에 별도 빈 TLS volume으로 교체해야 한다. 자동 갱신은 없다.

현재 네트워크 격리는 macOS sandbox-exec와 Colima/Lima 동작에 의존한다. macOS·Colima·Lima 업데이트 후 `check-host.py`와 재기동 검증을 다시 수행한다. 동일 macOS 사용자를 완전히 격리하는 구성은 아니다. 타인 초대 전에는 사용자별 계정·AI 키·인가·사용량 제한을 별도로 구현/검증한다.

참고: [Lima 포트 전달](https://lima-vm.io/docs/config/network/port/), [Access JWT 검증](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/), [VPC Service](https://developers.cloudflare.com/workers-vpc/configuration/vpc-services/).

## GitHub 자동 배포

`.github/workflows/check.yml`의 `check`가 GitHub 임시 runner에서 Python/프런트/Worker 검사, 앱·브로커 이미지 빌드와 실제 Docker sandbox 검사를 실행한다. PR은 검사만 한다. `main` push(문서만 변경한 경우 제외) 또는 수동 실행에서 검사를 통과하고 GitHub Variable `ENABLE_CD=true`이면 `deploy`가 `production` Deployment를 요청한다. 진행 중 workflow는 새 push로 취소하지 않는다.

Mac의 `com.code-trainer.deploy` LaunchAgent가 60초마다 요청을 확인한다. 고정 저장소명, 요청 생성자 `github-actions[bot]`, 최신 main SHA, workflow 경로, 실행 ID/재시도 번호, push/수동 이벤트와 성공한 check job, 진행 중 deploy job을 모두 검증한다. 실패/진행 중으로 기록된 요청은 자동 재시도하지 않는다. main 반영 권한은 운영 Mac에서 배포 코드를 실행할 수 있는 권한이다.

1. 외장 SSD의 전용 bare checkout에서 검사한 SHA를 fetch하고 `release/<SHA>` 작업 트리를 만든다. 개발 저장소의 미커밋 파일은 배포하지 않는다.
2. 화면을 빌드하고 앱 VM에서 앱·브로커 arm64 이미지를 만든다. 브로커 이미지는 archive로 실행 VM에 전달한다. 실행 VM의 외부 연결 차단을 유지한다. 두 이미지의 ID와 archive를 보존한다.
3. 오래 걸린 준비 후 GitHub의 최신 SHA/실행 상태를 다시 확인한다. 앱을 정지하고 **기존 앱 이미지**로 DB의 읽기 전용 볼륨에서 SQLite 사본과 암호화 백업을 만든다. 정기 백업과 겹치면 배포 전 백업은 실패하고 기존 앱을 재시작한다.
4. 백업 성공 후 브로커·앱의 image ID를 교체한다. health와 설치된 `check-host.py`의 실제 채점/mTLS/VM 격리 검사를 수행한다.
5. Mac의 기존 Wrangler 로그인으로 같은 SHA의 Worker/정적 화면을 게시한다. GitHub에 Cloudflare 토큰을 복사하지 않는다. 성공하면 `release/current`를 해당 SHA로 바꾸고 Deployment 성공을 보고한다.

배포 중에는 짧은 서비스 중단이 발생하고 진행 중 AI/채점 작업이 끊길 수 있다. 화면과 API는 순차 배포되므로 이전 화면과 호환되는 API 변경을 유지한다. Workers 게시 성공은 브라우저에서의 새 버전 실사용 검증을 대체하지 않는다.

실패 시:

- 빌드/설정 검사 실패: 기존 서비스를 유지한다.
- 정지 후 백업 실패: 기존 앱을 다시 시작하며 새 이미지를 적용하지 않는다.
- 새 백엔드 검증 실패: 새 앱을 중지하고 이전 코드로 자동 롤백하지 않는다. DB 변경 여부와 백업을 먼저 확인한다.
- Worker 게시 실패: 검증한 새 백엔드는 유지된다. GitHub는 실패로 표시하며 `release-state.json`의 단계를 확인한다.
- GitHub 대기 시간 초과 또는 Mac 전원 장애: Mac 작업이 계속되었거나 일부만 적용됐을 수 있다. 로그·컨테이너 이미지·Worker 버전·Deployment 상태를 확인한 다음 GitHub Actions에서 전체 workflow를 재실행한다.

호스트 기동/격리/Compose/배포 감시 코드와 sandbox 런타임 Dockerfile은 자동 갱신 대상에서 제외한다. `release.PROTECTED`의 파일이 설치 시 해시와 달라지면 서비스 중단 전에 배포를 거부한다. 해당 변경은 운영자가 검토하고 필요 작업을 적용한 뒤 `python3 deploy/install-cd.py`로 배포 감시 코드를 다시 설치한다. 이 명령은 sandbox 이미지를 빌드하거나 승인 목록을 바꾸지 않으므로 runtime 변경 시에는 별도 이미지 준비·검증·승인 목록 갱신이 필요하다. 이전 문제에서 쓰는 runtime image ID는 보존한다.

```sh
# 설치된 배포 감시 코드 갱신: 검토한 checkout에서 실행, Node 24 필요
python3 deploy/install-cd.py
# 자동 배포 켜기/끄기 (진행 중 요청은 취소하지 않음)
gh variable set ENABLE_CD --body true --repo Yelihi/code-trainer
gh variable set ENABLE_CD --body false --repo Yelihi/code-trainer
# 실행 상태와 Mac 로그
gh run list --workflow check.yml --repo Yelihi/code-trainer
tail -n 80 ~/.config/code-trainer/deploy.log
cat ~/.config/code-trainer/deployment/release-state.json
```

`Code Trainer Deploy.app`도 실제 LaunchAgent에서 외장 볼륨 접근 권한을 허용해야 한다. Node 설치 경로와 보호 파일 해시는 `~/.config/code-trainer/deployment/cd.json`, 직전 Compose 설정은 `compose.previous.env`에 둔다. 배포 요청 조회/상태 보고는 기존 Mac `gh` 인증을 사용한다. Wrangler 인증이 만료되면 Mac에서 재로그인한다. 두 인증의 비밀 값은 GitHub 저장소에 넣지 않는다. release/이미지 archive는 자동 삭제하지 않으므로 디스크를 관리한다.
