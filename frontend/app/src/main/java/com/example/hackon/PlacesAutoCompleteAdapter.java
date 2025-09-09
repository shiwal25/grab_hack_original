package com.example.hackon;

import android.content.Context;
import android.widget.ArrayAdapter;
import android.widget.Filter;
import android.widget.Filterable;

import com.google.android.gms.tasks.Tasks;
import com.google.android.libraries.places.api.model.AutocompletePrediction;
import com.google.android.libraries.places.api.model.AutocompleteSessionToken;
import com.google.android.libraries.places.api.net.FindAutocompletePredictionsRequest;
import com.google.android.libraries.places.api.net.PlacesClient;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;

public class PlacesAutoCompleteAdapter extends ArrayAdapter<String> implements Filterable {
    private List<AutocompletePrediction> predictionList = new ArrayList<>();
    private PlacesClient placesClient;
    private AutocompleteSessionToken token;

    public PlacesAutoCompleteAdapter(Context context, PlacesClient placesClient) {
        super(context, android.R.layout.simple_dropdown_item_1line);
        this.placesClient = placesClient;
        this.token = AutocompleteSessionToken.newInstance();
    }

    @Override
    public int getCount() {
        return predictionList.size();
    }

    @Override
    public String getItem(int position) {
        return predictionList.get(position).getFullText(null).toString();
    }

    public AutocompletePrediction getPrediction(int position) {
        return predictionList.get(position);
    }

    @Override
    public Filter getFilter() {
        return new Filter() {
            @Override
            protected FilterResults performFiltering(CharSequence constraint) {
                FilterResults results = new FilterResults();
                if (constraint != null) {
                    FindAutocompletePredictionsRequest request =
                            FindAutocompletePredictionsRequest.builder()
                                    .setSessionToken(token)
                                    .setQuery(constraint.toString())
                                    .build();

                    try {
                        List<AutocompletePrediction> predictions =
                                Tasks.await(placesClient.findAutocompletePredictions(request)).getAutocompletePredictions();
                        predictionList.clear();
                        predictionList.addAll(predictions);

                        List<String> suggestionList = new ArrayList<>();
                        for (AutocompletePrediction prediction : predictions) {
                            suggestionList.add(prediction.getFullText(null).toString());
                        }

                        results.values = suggestionList;
                        results.count = suggestionList.size();
                    } catch (ExecutionException | InterruptedException e) {
                        e.printStackTrace();
                    }
                }
                return results;
            }

            @Override
            protected void publishResults(CharSequence constraint, FilterResults results) {
                if (results != null && results.count > 0) {
                    clear();
                    addAll((List<String>) results.values);
                    notifyDataSetChanged();
                }
            }
        };
    }
}
