# 2. 관련 연구 및 기술 배경

## 2.1 Linux 서버 모니터링 시스템

서버 모니터링은 시스템의 자원 사용량과 프로세스 상태를 지속적으로 관찰하여 성능 저하나 장애의 징후를 파악하는 활동이다. 주요 목적은 성능 병목의 조기 발견, 자원의 효율적인 관리 및 서비스 중단 예방 등이다[1].

Linux 서버에서는 CPU 사용률과 부하 평균, 메모리 및 swap 사용량, 디스크 사용률, 네트워크 송수신량 등을 주요 지표로 사용한다. 이러한 정보는 `top`, `free`, `vmstat` 등의 명령어를 통해 확인할 수 있다[1][2]. 프로그램에서는 `/proc` 파일 시스템을 직접 읽거나 psutil과 같은 라이브러리를 사용하여 CPU, 메모리, 디스크, 네트워크 및 프로세스 정보를 수집할 수 있다[3]. 다만 psutil에는 CPU 사용률 측정처럼 일정 시간의 경과를 필요로 하는 호출이 포함되어 있다[3]. 이 특성은 수집 작업을 요청 처리 흐름과 분리해야 하는 이유가 되며, 3장의 상태 수집 구조에서 다시 다룬다.

이러한 지표는 서버 상태를 판단하는 데 중요하지만, 초보 학습자는 수치의 의미를 해석하는 데 어려움을 겪을 수 있다. 예를 들어 높은 CPU 사용률이 항상 장애를 의미하는 것은 아니며, Linux의 메모리 캐시 역시 실제 메모리 부족 상태와 구분해서 해석해야 한다. 따라서 학습용 모니터링 시스템은 단순한 수치 제공뿐 아니라 각 지표의 의미를 함께 설명할 필요가 있다.

## 2.2 웹 기반 시스템 관리 도구

웹 기반 시스템 관리 도구는 브라우저를 통해 서버 상태를 확인하고 원격에서 시스템을 관리할 수 있도록 한다. 수치와 그래프를 활용해 서버 상태를 시각화할 수 있으며, 여러 사용자가 운영체제와 관계없이 접근할 수 있다는 장점이 있다.

대표적인 도구로는 Prometheus, Grafana, Netdata, Cockpit 등이 있다. Prometheus는 시스템 지표를 수집하고 저장하는 데 사용되며, Grafana는 수집된 데이터를 대시보드 형태로 시각화한다[4][5]. Netdata는 서버에 에이전트를 설치하여 실시간 지표를 제공하며[6], Cockpit은 단일 Linux 서버를 웹에서 관리할 수 있는 기능을 제공한다[7].

| 도구                 | 주요 목적        | 시각화   | 학습 지원   |
| ------------------ | ------------ | ----- | ------- |
| Prometheus·Grafana | 지표 수집·저장·시각화 | 제공    | 제공하지 않음 |
| Netdata            | 실시간 자원 관찰    | 제공    | 제공하지 않음 |
| Cockpit            | 단일 서버 관리     | 기본 제공 | 제공하지 않음 |
| Zabbix·Nagios      | 장애 감지 및 알림   | 제공    | 제공하지 않음 |

[표 2-1] 기존 웹 기반 모니터링 도구의 기능

기존 도구들은 실제 서버 운영과 장애 감지를 목적으로 개발되었기 때문에, 전문적인 용어와 기능을 전제로 한다. 또한 서버 상태의 수치와 그래프는 제공하지만 해당 값이 무엇을 의미하는지 설명하거나, 학습 과제와 피드백을 제공하지는 않는다. 이는 운영 도구의 결함이라기보다 설계 목적의 차이지만, 초보 학습자가 기존 도구만으로 서버 운영을 학습하기에는 한계가 있다. 학습을 목적으로 설계된 플랫폼은 2.3절에서 별도로 살펴본다.

## 2.3 시뮬레이션 기반 실습 환경

Linux 서버 운영은 명령어를 직접 입력하고 결과를 확인하는 과정이 중요하다. 그러나 초보 학습자가 실제 서버에서 서비스를 중지하거나 방화벽과 파일 권한을 잘못 설정하면 시스템 장애가 발생할 수 있다. 여러 사용자가 하나의 서버를 공유하는 환경에서는 이러한 문제가 다른 사용자에게까지 영향을 줄 수 있다. 가상 실습 환경에 관한 연구들은 반복 수행 가능성 및 비용 절감과 함께 학습자의 안전 확보와 위험한 실험의 수행 가능성을 공통된 이점으로 제시한다[8].

안전한 실습 환경을 제공하는 방식은 가상머신, 컨테이너 및 상태 시뮬레이션으로 구분할 수 있다.

| 방식       | 자원 사용량 | 격리 수준     | 실제 명령 실행 |
| -------- | ------ | --------- | -------- |
| 가상머신     | 높음     | 높음        | 가능       |
| 컨테이너     | 비교적 낮음 | 중간        | 가능       |
| 상태 시뮬레이션 | 매우 낮음  | 실행 자체가 없음 | 불가능      |

[표 2-2] 실습 환경 구성 방식 비교

가상머신은 운영체제 전체를 격리하므로 안전성이 높지만 학습자마다 많은 자원이 필요하다. 컨테이너는 가상머신보다 가볍고 빠르게 생성할 수 있지만 호스트의 커널을 공유한다는 한계가 있다[9][10][11]. 상태 시뮬레이션은 명령어를 실제로 실행하지 않고 구조화된 가상 상태만 변경하는 방식이다. 실제 실행 경험은 제공하지 못하지만, 시스템 자원 사용량이 적고 위험한 명령도 안전하게 학습할 수 있다.

Linux Luminarium, KillerCoda 및 OverTheWire Bandit과 같은 플랫폼은 웹 환경에서 Linux 명령어와 시스템 관리 과제를 제공한다[12][13][14]. 이 가운데 Linux Luminarium과 Bandit은 단순히 정답 명령어 문자열을 비교하기보다, 학습자가 요구된 상태에 도달했는지를 기준으로 진행 여부를 판단한다[12][14].

특정 명령어 문자열만을 기준으로 채점하면 같은 목표를 다른 명령어나 순서로 달성한 경우를 인정하기 어렵다. 시스템 관리 과제의 자동 채점을 다룬 연구들도 과제의 성취를 명령이 아니라 운영체제 전체의 상태로 확인해야 한다는 문제의식 아래, 실행 중인 가상머신의 상태를 검사하는 방향으로 발전해 왔다[15]. 따라서 본 연구에서는 학습자가 입력한 명령어 자체가 아니라, 명령 처리 후의 최종 가상 상태가 목표 조건을 충족했는지를 기준으로 학습 결과를 판정한다.

## 2.4 생성형 AI와 학습 지원 시스템

생성형 AI는 자연어 기반의 질의응답, 개념 설명, 오류 원인 안내 및 학습자 수준에 따른 설명 조정 기능을 제공할 수 있다. 프로그래밍 교육 관련 연구에서는 생성형 AI가 즉각적인 피드백과 맞춤형 설명을 제공할 수 있다는 장점이 보고되었다[16][17][18]. 다만 같은 연구들은 초보 학습자에게는 구조화된 안내가 필요하다는 점[16]과, 생성형 AI에 대한 과도한 의존이 비판적 사고를 저하시킬 수 있다는 우려[17][18]를 함께 지적한다. 이는 정답을 바로 제시하기보다 단계적으로 안내하는 힌트 구조가 필요한 이유가 된다.

반면 생성형 AI는 사실과 다른 내용을 자연스럽게 생성하는 환각 문제가 있다[19]. 학습 지원 시스템에서 잘못된 설명이나 힌트가 제공되면 학습자는 이를 직접 판별하기 어렵고, 잘못된 개념을 학습할 수 있다. 실제로 지능형 튜터링 시스템에 언어모델 피드백을 결합한 연구는 생성된 힌트 가운데 상당수가 지나치게 일반적이거나, 부정확하거나, 정답을 그대로 노출하는 문제를 보였다고 보고하였다[20]. 또한 환각이 포함된 피드백이 학습자의 학습 성과와 혼란 정도, 과제 수행 시간, 시스템에 대한 신뢰에 부정적 영향을 준다는 실증 연구도 제시되어 있다[21].

이러한 문제를 줄이기 위해서는 생성형 AI가 판단해야 하는 범위를 제한할 필요가 있다. 시스템이 이미 확정한 상태, 정답 여부 및 학습 단계를 생성형 AI에 함께 제공하면, AI가 결과를 직접 추정하지 않고 확정된 정보를 설명하는 데 집중할 수 있다[19][20].

따라서 본 연구에서는 학습자의 성공 여부와 서버 상태를 규칙 기반으로 판정하고, 생성형 AI는 해당 판정의 이유와 관련 Linux 개념을 설명하는 역할만 담당하도록 구성하였다.

## 2.5 Amazon Bedrock

Amazon Bedrock은 여러 파운데이션 모델을 API 방식으로 사용할 수 있도록 제공하는 AWS의 관리형 서비스이다. 모델의 운영과 확장은 서비스 제공자가 담당하며, 응용 프로그램은 모델을 직접 구축하지 않고 API 호출을 통해 생성형 AI 기능을 사용할 수 있다[22].

본 연구에서는 Amazon Bedrock의 Converse API를 사용한다. Converse API는 서로 다른 대화형 모델에 공통된 호출 형식을 제공하여, 사용하는 모델이 변경되더라도 응용 프로그램의 수정 범위를 줄일 수 있다[23][24].

Amazon Bedrock을 선택한 이유는 세 가지이다. 첫째, 학습자의 질문과 실습 상태가 외부 모델 서비스로 전달되므로 입력 데이터의 취급이 중요한데, Converse API 공식 문서는 제공된 입력 콘텐츠를 저장하지 않고 응답 생성에만 사용한다고 명시하고 있다[23]. 둘째, 모델 접근 자격 증명을 응용 프로그램에 별도로 유통하지 않고 AWS IAM의 권한 체계로 일원화할 수 있다. 셋째, 통합 대화 API를 사용하면 특정 모델에 대한 종속성을 줄일 수 있다.

## 2.6 기존 연구와의 차별성

기존 연구와 도구는 서버 상태 시각화, 가상 실습 환경 및 생성형 AI 학습 지원이라는 개별 영역에서 발전해 왔다. 본 연구는 이러한 기능을 하나의 웹 기반 학습 프로그램으로 통합하고, 학습 결과의 판정과 생성형 AI의 설명 역할을 분리했다는 점에서 차이가 있다.

| 구분        | 기존 연구·도구                | 본 연구                  |
| --------- | ----------------------- | --------------------- |
| 서버 상태 제공  | 수치와 그래프 중심              | 상태 시각화와 가상 실습 상태의 자연어 설명 |
| 대상 사용자    | 서버 운영 전문가 중심            | Linux 서버 운영 초보 학습자 중심 |
| 실습 방식     | 실제 가상머신 또는 컨테이너에서 명령 실행 | 가상 상태 전이 실습, 실제 실행은 별도 터미널 |
| 학습 결과 판정  | 명령 문자열 또는 실제 시스템 상태 확인[15]  | 최종 가상 상태를 기준으로 판정     |
| 생성형 AI 역할 | 설명과 판단을 함께 수행할 수 있음     | 서버가 판정하고 AI는 결과만 설명   |

[표 2-3] 기존 연구·도구와 본 연구의 차이

본 연구는 모니터링 화면에서 자원 사용량을 관찰하는 경험과, 가상 실습에서 명령의 의미를 자연어로 설명받는 경험을 하나의 학습 프로그램 안에서 제공한다. 다만 생성형 AI가 설명하는 대상은 가상 실습 상태이며, 모니터링 화면의 자원 사용량은 시각화로 제시할 뿐 자연어로 해설하지 않는다. 또한 학습 시나리오에서 입력한 명령은 실제로 실행하지 않고 가상 상태만 변경하므로, 서비스 중지나 방화벽 차단과 같이 위험한 명령도 안전하게 학습 소재로 삼을 수 있다. 실제 명령을 실행해 보는 경험은 이와 분리된 웹 터미널이 격리된 컨테이너 안에서 제공하며, 두 기능은 상태를 공유하지 않는다.

특히 학습 결과는 서버 내부의 규칙으로 판정하고, 생성형 AI는 확정된 결과를 설명하는 역할로 제한하였다. 이는 생성형 AI의 부정확한 응답이 학습자의 성취 판정에 직접 영향을 미치는 문제를 줄이기 위한 것이다. 다음 장에서는 이러한 배경을 바탕으로 설계한 시스템의 구성과 주요 기능을 설명한다.

---

## 이 장에서 인용한 자료

> 최종 참고문헌으로 옮길 때 학교 양식에 맞추어 서지 정보를 보완한다. 웹 문서는 접속일자를
> 함께 표기한다.

[1] Linux Journal, "Stay Ahead of the Game: Essential Tools and Techniques for Linux Server Monitoring."
https://www.linuxjournal.com/content/stay-ahead-game-essential-tools-and-techniques-linux-server-monitoring

[2] Linux man-pages, `proc(5)`, `free(1)`, `top(1)`. https://man7.org/linux/man-pages/

[3] psutil documentation. https://psutil.readthedocs.io/

[4] Prometheus Documentation, "Overview." https://prometheus.io/docs/introduction/overview/

[5] Grafana Documentation. https://grafana.com/docs/

[6] Netdata Documentation. https://www.netdata.cloud/

[7] Cockpit Project. https://cockpit-project.org/

[8] "Evaluating virtual laboratory platforms for supporting on-line information security courses," arXiv:2208.12612.

[9] B. Sharma et al., "Containers and Virtual Machines at Scale: A Comparative Study," ACM/IFIP/USENIX Middleware, 2016.

[10] H. Aqasizade et al., "Experimental assessment of containers running on top of virtual machines," IET Networks, 2025.

[11] "Virtual Machines vs. Containerized Environments," Saudi Journal of Engineering and Technology.

[12] Z. Nelson et al., "The Linux Luminarium: Learning Linux by Leveraging …," ACM SIGCSE Technical Symposium, 2026.

[13] KillerCoda. https://killercoda.com/

[14] OverTheWire, "Bandit." https://overthewire.org/wargames/

[15] "Automated online grading for virtual machine-based systems administration courses."

[16] "Teaching with AI: A Systematic Review of Chatbots, Generative Tools, and Tutoring Systems in Programming Education," IJLTER, 2025.

[17] "Teaching and learning computer programming using ChatGPT: A rapid review," Education and Information Technologies, 2025.

[18] "Generative AI for Programming Education: Can ChatGPT Facilitate …," ACM ICCA, 2025.

[19] "Large Language Models Hallucination: A Comprehensive Survey," arXiv:2510.06265.

[20] "Generating In-Context, Personalized Feedback for Intelligent Tutors with Large Language Models," International Journal of Artificial Intelligence in Education, 2025.

[21] "When LLMs Hallucinate: Examining the Effects of Erroneous Feedback in Math Tutoring Systems," ACM Learning @ Scale, 2025.

[22] AWS Documentation, "What is Amazon Bedrock." https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html

[23] AWS API Reference, "Converse." https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html

[24] AWS What's New, "Amazon Bedrock announces new Converse API," 2024-05-30.
