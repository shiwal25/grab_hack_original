package com.example.hackon;

import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.SpeechRecognizer;
import android.view.View;
import android.widget.EditText;
import android.widget.ImageButton;

import java.util.ArrayList;

public class recognitionListener implements RecognitionListener {

    View view;
    EditText scenarioText;
    ImageButton micButton;
    SpeechRecognizer speechRecognizer;
    recognitionListener(View view, SpeechRecognizer speechRecognizer){
        this.view = view;
        scenarioText = view.findViewById(R.id.scenarioText);
        micButton = view.findViewById(R.id.sendAudioBtn);
        this.speechRecognizer = speechRecognizer;
    }
    @Override
    public void onReadyForSpeech(Bundle bundle) {
    }

    @Override
    public void onBeginningOfSpeech() {

    }

    @Override
    public void onRmsChanged(float v) {

    }

    @Override
    public void onBufferReceived(byte[] bytes) {

    }

    @Override
    public void onEndOfSpeech() {

    }

    @Override
    public void onError(int i) {
        micButton.setImageResource(R.drawable.ic_microphone);
    }

    @Override
    public void onResults(Bundle bundle) {
        ArrayList<String>  result = bundle.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if(result != null && !result.isEmpty()){
            scenarioText.setText(result.get(0));
        }
        micButton.setImageResource(R.drawable.ic_microphone);
        speechRecognizer.stopListening();
    }

    @Override
    public void onPartialResults(Bundle bundle) {

    }

    @Override
    public void onEvent(int i, Bundle bundle) {

    }
}
