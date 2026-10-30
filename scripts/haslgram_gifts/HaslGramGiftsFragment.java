/*
 * HaslGram read-only catalog screen.
 * Original app and RLottie code: Telegram / OwpenGram, GPL-2.0-or-later.
 * This screen only reads a HaslGram-hosted, dated Telegram gift metadata snapshot.
 * It does not sell, transfer, own, or upgrade gifts.
 */
package org.telegram.ui;

import android.content.Context;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BackDrawable;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.RLottieDrawable;
import org.telegram.ui.Components.RLottieImageView;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native, strictly read-only UI for the public HaslGram official-source catalog. */
public class HaslGramGiftsFragment extends BaseFragment {
    private static final String BASE_URL = "https://api.haslgram.site/gifts/v1/";
    private static final ExecutorService NETWORK = Executors.newFixedThreadPool(3);
    private final ArrayList<Gift> allGifts = new ArrayList<>();
    private final ArrayList<Gift> visibleGifts = new ArrayList<>();
    private GiftAdapter adapter;
    private TextView notice;
    private final ArrayList<TextView> filters = new ArrayList<>();
    private int selectedFilter;
    private boolean destroyed;
    private String snapshotDate = "";

    private static class Gift {
        String id;
        String documentId;
        String sha256;
        String mediaPath;
        long telegramStars;
        boolean soldOut;
        boolean upgradable;
    }

    @Override
    public View createView(Context context) {
        destroyed = false;
        actionBar.setBackButtonDrawable(new BackDrawable(false));
        actionBar.setTitle("Подарки HaslGram");
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });

        LinearLayout root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        fragmentView = root;

        notice = text(context, 13, Theme.key_windowBackgroundWhiteGrayText);
        notice.setPadding(dp(16), dp(12), dp(16), dp(12));
        notice.setText("Загрузка каталога…");
        notice.setOnClickListener(v -> loadCatalog());
        root.addView(notice, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout tabs = new LinearLayout(context);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setPadding(dp(12), dp(2), dp(12), dp(8));
        addFilter(context, tabs, "Все", 0);
        addFilter(context, tabs, "Не распроданы", 1);
        addFilter(context, tabs, "С улучшением", 2);
        root.addView(tabs, new LinearLayout.LayoutParams(-1, -2));

        RecyclerView list = new RecyclerView(context);
        list.setLayoutManager(new LinearLayoutManager(context));
        adapter = new GiftAdapter();
        list.setAdapter(adapter);
        root.addView(list, new LinearLayout.LayoutParams(-1, 0, 1f));
        updateFilters();
        loadCatalog();
        return fragmentView;
    }

    private static int dp(int value) {
        return AndroidUtilities.dp(value);
    }

    private TextView text(Context context, int sp, int themeKey) {
        TextView view = new TextView(context);
        view.setTextSize(sp);
        view.setTextColor(Theme.getColor(themeKey));
        return view;
    }

    private void addFilter(Context context, LinearLayout tabs, String title, int number) {
        TextView filter = text(context, 13, Theme.key_windowBackgroundWhiteBlackText);
        filter.setText(title);
        filter.setGravity(Gravity.CENTER);
        filter.setPadding(dp(3), dp(10), dp(3), dp(10));
        filter.setOnClickListener(v -> {
            selectedFilter = number;
            updateFilters();
            showFiltered();
        });
        tabs.addView(filter, new LinearLayout.LayoutParams(0, -2, 1f));
        filters.add(filter);
    }

    private void updateFilters() {
        for (int i = 0; i < filters.size(); i++) {
            TextView tab = filters.get(i);
            tab.setAlpha(i == selectedFilter ? 1f : 0.58f);
            tab.setTypeface(null, i == selectedFilter ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
        }
    }

    private void showFiltered() {
        visibleGifts.clear();
        for (Gift gift : allGifts) {
            if (selectedFilter == 1 && gift.soldOut) continue;
            if (selectedFilter == 2 && !gift.upgradable) continue;
            visibleGifts.add(gift);
        }
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
    }

    private void loadCatalog() {
        if (notice == null || destroyed) return;
        notice.setText("Загрузка каталога Telegram…");
        NETWORK.execute(() -> {
            try {
                JSONObject data = new JSONObject(new String(
                    getBytes(BASE_URL + "catalog.json", 1024 * 1024), StandardCharsets.UTF_8));
                if (!data.optBoolean("read_only") ||
                    !data.optBoolean("prices_are_telegram_stars_not_hasl_stars")) {
                    throw new IOException("Неподдерживаемый формат каталога");
                }
                JSONArray items = data.getJSONArray("gifts");
                if (items.length() == 0 || items.length() > 1000 ||
                    items.length() != data.getInt("gift_count")) {
                    throw new IOException("Некорректное количество подарков");
                }
                ArrayList<Gift> parsed = new ArrayList<>();
                Set<String> seen = new HashSet<>();
                for (int i = 0; i < items.length(); i++) {
                    JSONObject item = items.getJSONObject(i);
                    Gift gift = new Gift();
                    gift.id = item.getString("gift_id");
                    gift.documentId = item.getString("document_id");
                    gift.sha256 = item.getString("document_sha256");
                    gift.mediaPath = item.getString("animation_path");
                    gift.telegramStars = item.getLong("telegram_price_stars");
                    gift.soldOut = item.getBoolean("sold_out_at_capture");
                    gift.upgradable = item.getBoolean("supports_upgrade_by_type");
                    if (!gift.id.matches("[0-9]{1,20}") ||
                        !gift.documentId.matches("[0-9]{1,20}") ||
                        !gift.sha256.matches("[a-fA-F0-9]{64}") ||
                        !gift.mediaPath.equals("media/" + gift.documentId + ".tgs") ||
                        gift.telegramStars <= 0 ||
                        item.optBoolean("purchasable_in_haslgram", true) ||
                        !seen.add(gift.id)) {
                        throw new IOException("Некорректные данные подарка");
                    }
                    parsed.add(gift);
                }
                final String capturedAt = data.optString("captured_at_utc", "");
                AndroidUtilities.runOnUIThread(() -> {
                    if (destroyed) return;
                    allGifts.clear();
                    allGifts.addAll(parsed);
                    snapshotDate = capturedAt;
                    showFiltered();
                    notice.setText("Снимок Telegram" +
                        (snapshotDate.isEmpty() ? "" : " от " + snapshotDate) +
                        ". " + allGifts.size() + " подарков.\n" +
                        "Покупка и улучшение в HaslGram пока недоступны. " +
                        "Цены ниже — в Telegram Stars, не в Hasl Stars. " +
                        "Нажмите здесь, чтобы обновить.");
                });
            } catch (Exception ex) {
                AndroidUtilities.runOnUIThread(() -> {
                    if (!destroyed) {
                        notice.setText("Не удалось получить каталог подарков. " +
                            "Проверьте подключение и нажмите для повтора.");
                    }
                });
            }
        });
    }

    private static byte[] getBytes(String url, int maxBytes) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(15000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("Accept-Encoding", "identity");
        try {
            if (connection.getResponseCode() != 200) {
                throw new IOException("HTTP " + connection.getResponseCode());
            }
            try (InputStream in = connection.getInputStream();
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int count;
                while ((count = in.read(buffer)) != -1) {
                    if (out.size() + count > maxBytes) {
                        throw new IOException("Слишком большой ответ сервера");
                    }
                    out.write(buffer, 0, count);
                }
                return out.toByteArray();
            }
        } finally {
            connection.disconnect();
        }
    }

    private static String digest(byte[] bytes) throws Exception {
        byte[] sha = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder result = new StringBuilder(64);
        for (byte b : sha) {
            result.append(String.format(Locale.US, "%02x", b & 0xff));
        }
        return result.toString();
    }

    private static byte[] readBounded(File file, int limit) throws IOException {
        if (!file.isFile() || file.length() > limit || file.length() < 2) {
            throw new IOException("Неверный файл");
        }
        try (FileInputStream in = new FileInputStream(file);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = in.read(buffer)) != -1) {
                if (out.size() + count > limit) throw new IOException("Файл слишком большой");
                out.write(buffer, 0, count);
            }
            return out.toByteArray();
        }
    }

    private static boolean verified(byte[] bytes, String sha) throws Exception {
        return bytes.length >= 2 &&
            (bytes[0] & 0xff) == 0x1f && (bytes[1] & 0xff) == 0x8b &&
            digest(bytes).equalsIgnoreCase(sha);
    }

    private static File mediaFile(Gift gift) throws Exception {
        File directory = new File(ApplicationLoader.applicationContext.getCacheDir(), "haslgram-gifts-v1");
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IOException("Нет доступа к кэшу");
        }
        File destination = new File(directory, gift.documentId + ".tgs");
        try {
            if (verified(readBounded(destination, 512 * 1024), gift.sha256)) {
                return destination;
            }
        } catch (Exception ignored) {
            // Missing, partial or outdated cache: fetch original document again.
        }
        byte[] bytes = getBytes(BASE_URL + gift.mediaPath, 512 * 1024);
        if (!verified(bytes, gift.sha256)) {
            throw new IOException("SHA-256 анимации не соответствует каталогу");
        }
        File temp = File.createTempFile("gift-", ".part", directory);
        try {
            try (FileOutputStream out = new FileOutputStream(temp)) {
                out.write(bytes);
            }
            if (destination.exists() && !destination.delete()) {
                throw new IOException("Не удалось заменить кэш");
            }
            if (!temp.renameTo(destination)) {
                throw new IOException("Не удалось сохранить анимацию");
            }
            return destination;
        } finally {
            if (temp.exists()) temp.delete();
        }
    }

    private class GiftHolder extends RecyclerView.ViewHolder {
        final RLottieImageView animation;
        final TextView title;
        final TextView price;
        final TextView status;
        String boundId = "";

        GiftHolder(Context context) {
            super(new LinearLayout(context));
            LinearLayout row = (LinearLayout) itemView;
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(12), dp(8), dp(12), dp(8));

            animation = new RLottieImageView(context);
            animation.setAutoRepeat(true);
            row.addView(animation, new LinearLayout.LayoutParams(dp(88), dp(88)));

            LinearLayout labels = new LinearLayout(context);
            labels.setOrientation(LinearLayout.VERTICAL);
            labels.setPadding(dp(12), 0, 0, 0);
            row.addView(labels, new LinearLayout.LayoutParams(0, -2, 1f));

            title = text(context, 15, Theme.key_windowBackgroundWhiteBlackText);
            labels.addView(title);
            price = text(context, 13, Theme.key_windowBackgroundWhiteGrayText);
            labels.addView(price);
            status = text(context, 13, Theme.key_windowBackgroundWhiteGrayText);
            labels.addView(status);
        }

        void clearAnimation() {
            RLottieDrawable old = animation.getAnimatedDrawable();
            animation.stopAnimation();
            animation.clearAnimationDrawable();
            if (old != null) old.recycle(false);
        }
    }

    private class GiftAdapter extends RecyclerView.Adapter<GiftHolder> {
        @Override
        public GiftHolder onCreateViewHolder(ViewGroup parent, int viewType) {
            return new GiftHolder(parent.getContext());
        }

        @Override
        public void onBindViewHolder(GiftHolder holder, int position) {
            Gift gift = visibleGifts.get(position);
            holder.boundId = gift.id;
            holder.clearAnimation();
            holder.title.setText("Подарок #" + gift.id);
            holder.price.setText("Telegram Stars: " + gift.telegramStars);
            holder.status.setText(
                (gift.soldOut ? "Распродан на момент снимка" : "Был доступен на момент снимка")
                + (gift.upgradable ? " · Улучшаемый тип" : ""));
            holder.itemView.setOnClickListener(v -> {
                Context context = holder.itemView.getContext();
                new android.app.AlertDialog.Builder(context)
                    .setTitle("Подарок #" + gift.id)
                    .setMessage("Цена в Telegram: " + gift.telegramStars + " Stars\n" +
                        (gift.soldOut ? "Распродан на момент снимка" : "Был доступен на момент снимка") +
                        "\n" + (gift.upgradable ? "Тип допускает улучшение" : "Тип не допускает улучшение") +
                        "\n\nПокупка и улучшение в HaslGram пока недоступны.")
                    .setPositiveButton("Закрыть", null)
                    .show();
            });
            NETWORK.execute(() -> {
                try {
                    if (destroyed) return;
                    File file = mediaFile(gift);
                    AndroidUtilities.runOnUIThread(() -> {
                        // RLottieImageView can prepare the drawable before attachment
                        // and will start it when the recycled row enters the viewport.
                        if (destroyed || !gift.id.equals(holder.boundId)) return;
                        try {
                            holder.clearAnimation();
                            RLottieDrawable drawable = new RLottieDrawable(
                                file, null, dp(88), dp(88), null, false, null, 0, false);
                            holder.animation.setAnimation(drawable);
                            holder.animation.playAnimation();
                        } catch (Exception ignored) {
                            holder.clearAnimation();
                        }
                    });
                } catch (Exception ignored) {
                    // Broken or unavailable media must not break the catalog UI.
                }
            });
        }

        @Override
        public int getItemCount() {
            return visibleGifts.size();
        }

        @Override
        public void onViewRecycled(GiftHolder holder) {
            holder.boundId = "";
            holder.clearAnimation();
            super.onViewRecycled(holder);
        }
    }

    @Override
    public void onFragmentDestroy() {
        destroyed = true;
        super.onFragmentDestroy();
    }
}
