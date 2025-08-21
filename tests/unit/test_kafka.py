"""
Unit tests for Kafka messaging operations
Kafka 메시징 작업을 위한 단위 테스트
"""

import pytest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from messaging.kafka_client import KafkaProducer

class TestKafkaProducer:
    """Test cases for KafkaProducer class"""

    @patch('messaging.kafka_client.KafkaProducer')
    def test_kafka_producer_initialization(self, mock_kafka_producer_class):
        """Test KafkaProducer initialization"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        
        producer = KafkaProducer()
        
        assert producer.producer == mock_producer_instance
        mock_kafka_producer_class.assert_called_once()

    @patch('messaging.kafka_client.KafkaProducer')
    def test_publish_coupon_issued_success(self, mock_kafka_producer_class):
        """Test successful coupon issued event publishing"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        mock_producer_instance.send.return_value.get.return_value = True
        
        producer = KafkaProducer()
        result = producer.publish_coupon_issued("user123", "event123", "coupon123")
        
        assert result is True
        
        # Verify the message was sent with correct data
        expected_message = {
            "event_type": "coupon_issued",
            "user_id": "user123",
            "event_id": "event123",
            "coupon_id": "coupon123",
            "timestamp": mock_producer_instance.send.call_args[1]["value"]["timestamp"]
        }
        
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args
        assert call_args[0][0] == "coupon-events"  # topic
        assert call_args[1]["key"] == b"user123"
        
        sent_message = call_args[1]["value"]
        assert sent_message["event_type"] == "coupon_issued"
        assert sent_message["user_id"] == "user123"
        assert sent_message["event_id"] == "event123"
        assert sent_message["coupon_id"] == "coupon123"

    @patch('messaging.kafka_client.KafkaProducer')
    def test_publish_coupon_issued_failure(self, mock_kafka_producer_class):
        """Test failed coupon issued event publishing"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        mock_producer_instance.send.side_effect = Exception("Kafka error")
        
        producer = KafkaProducer()
        result = producer.publish_coupon_issued("user123", "event123", "coupon123")
        
        assert result is False

    @patch('messaging.kafka_client.KafkaProducer')
    def test_publish_stock_exhausted_success(self, mock_kafka_producer_class):
        """Test successful stock exhausted event publishing"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        mock_producer_instance.send.return_value.get.return_value = True
        
        producer = KafkaProducer()
        result = producer.publish_stock_exhausted("event123", 0)
        
        assert result is True
        
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args
        assert call_args[0][0] == "coupon-events"
        assert call_args[1]["key"] == b"event123"
        
        sent_message = call_args[1]["value"]
        assert sent_message["event_type"] == "stock_exhausted"
        assert sent_message["event_id"] == "event123"
        assert sent_message["remaining_stock"] == 0

    @patch('messaging.kafka_client.KafkaProducer')
    def test_publish_stock_exhausted_failure(self, mock_kafka_producer_class):
        """Test failed stock exhausted event publishing"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        mock_producer_instance.send.side_effect = Exception("Kafka error")
        
        producer = KafkaProducer()
        result = producer.publish_stock_exhausted("event123", 0)
        
        assert result is False

    @patch('messaging.kafka_client.KafkaProducer')
    def test_close_producer(self, mock_kafka_producer_class):
        """Test closing Kafka producer"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        
        producer = KafkaProducer()
        producer.close()
        
        mock_producer_instance.close.assert_called_once()

    @patch('messaging.kafka_client.KafkaProducer')
    def test_message_serialization(self, mock_kafka_producer_class):
        """Test message serialization for Kafka"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer_class.return_value = mock_producer_instance
        mock_producer_instance.send.return_value.get.return_value = True
        
        producer = KafkaProducer()
        producer.publish_coupon_issued("user123", "event123", "coupon123")
        
        # Check that the message can be serialized to JSON
        call_args = mock_producer_instance.send.call_args
        sent_message = call_args[1]["value"]
        
        # This should not raise an exception
        json_string = json.dumps(sent_message)
        parsed_message = json.loads(json_string)
        
        assert parsed_message["event_type"] == "coupon_issued"
        assert parsed_message["user_id"] == "user123"