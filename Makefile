run:
	python app.py

verify-hw02:
	python verify_hw02.py

verify-hw03:
	python verify_hw03.py

verify-hw04:
	python verify_hw04.py

verify-hw05:
	python verify_hw05.py

test-tools:
	python test_tools.py

verify-hw06:
	python verify_hw06.py

verify-hw07:
	python verify_hw07.py

KAFKA_TOPICS = docker exec s0571-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092

kafka-topics:
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_notice_requests --partitions 1 --replication-factor 1
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_notice_responses --partitions 1 --replication-factor 1
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_inbox --partitions 1 --replication-factor 1
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_tasks --partitions 2 --replication-factor 1
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_drafts --partitions 1 --replication-factor 1
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_final --partitions 1 --replication-factor 1
	$(KAFKA_TOPICS) --create --if-not-exists --topic s0571_dead_letter --partitions 1 --replication-factor 1

verify-hw08:
	python verify_hw08.py

verify-hw09:
	python verify_hw09.py
