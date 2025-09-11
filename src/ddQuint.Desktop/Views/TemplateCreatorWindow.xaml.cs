using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using ddQuint.Desktop.Properties;
using ddQuint.Desktop.Services;

namespace ddQuint.Desktop.Views
{
    public partial class TemplateCreatorWindow : Window
    {
        private readonly PythonEnvironmentService _python;

        private List<string> _disp = new();
        private List<string> _c1 = new();
        private List<string> _c2 = new();
        private List<string> _c3 = new();
        private List<string> _c4 = new();
        private string? _selectedNamesPath;

        public TemplateCreatorWindow()
        {
            InitializeComponent();
            _python = PythonEnvironmentService.Instance;
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            // Populate dropdowns
            SupermixCombo.ItemsSource = new[]
            {
                "ddPCR Supermix for Probes (No dUTP)",
                "ddPCR EvaGreen Supermix",
                "ddPCR Supermix for Probes",
                "ddPCR Multiplex Supermix",
                "ddPCR Supermix for Residual DNA Quantification"
            };
            AssayCombo.ItemsSource = new[]
            {
                "Probe Mix Triplex",
                "Amplitude Multiplex",
                "Single Target per Channel"
            };
            ExperimentCombo.ItemsSource = new[]
            {
                "Copy Number Variation (CNV)",
                "Direct Quantification (DQ)",
                "Mutation Detection (MUT)",
                "Rare Event Detection (RED)",
                "Drop Off (DOF)",
                "Gene Expression (GEX)",
                "Residual DNA Quantification (RDQ)"
            };

            // Load persisted selections
            TrySelect(SupermixCombo, Settings.Default.TemplateCreator_Supermix, 0);
            TrySelect(AssayCombo, Settings.Default.TemplateCreator_Assay, 0);
            TrySelect(ExperimentCombo, Settings.Default.TemplateCreator_Experiment, 0);
            Target1.Text = Settings.Default.TemplateCreator_Target1 ?? string.Empty;
            Target2.Text = Settings.Default.TemplateCreator_Target2 ?? string.Empty;
            Target3.Text = Settings.Default.TemplateCreator_Target3 ?? string.Empty;
            Target4.Text = Settings.Default.TemplateCreator_Target4 ?? string.Empty;

            UpdateTargetHint();
            ResetPreview();
        }

        private static void TrySelect(ComboBox box, string? value, int fallbackIndex)
        {
            if (!string.IsNullOrWhiteSpace(value) && box.Items.Contains(value))
                box.SelectedItem = value;
            else
                box.SelectedIndex = fallbackIndex;
        }

        private void OnAssayChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateTargetHint();
            SaveSelections();
        }

        private void OnSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            SaveSelections();
        }

        private void OnTargetChanged(object sender, TextChangedEventArgs e)
        {
            SaveSelections();
        }

        private string RealTextOrEmpty(TextBox box)
        {
            var wm = TextBoxHelper.GetWatermark(box);
            var isPlaceholder = box.Foreground == Brushes.Gray && string.Equals(box.Text, wm, StringComparison.Ordinal);
            return isPlaceholder ? string.Empty : (box.Text ?? string.Empty);
        }

        private void SaveSelections()
        {
            try
            {
                Settings.Default.TemplateCreator_Supermix = SupermixCombo.SelectedItem as string ?? string.Empty;
                Settings.Default.TemplateCreator_Assay = AssayCombo.SelectedItem as string ?? string.Empty;
                Settings.Default.TemplateCreator_Experiment = ExperimentCombo.SelectedItem as string ?? string.Empty;
                Settings.Default.TemplateCreator_Target1 = RealTextOrEmpty(Target1);
                Settings.Default.TemplateCreator_Target2 = RealTextOrEmpty(Target2);
                Settings.Default.TemplateCreator_Target3 = RealTextOrEmpty(Target3);
                Settings.Default.TemplateCreator_Target4 = RealTextOrEmpty(Target4);
                Settings.Default.Save();
            }
            catch { }
        }

        private void UpdateTargetHint()
        {
            var assay = (AssayCombo.SelectedItem as string)?.ToLowerInvariant() ?? string.Empty;
            var supermix = (SupermixCombo.SelectedItem as string) ?? string.Empty;
            var famSignal = supermix.ToLowerInvariant().Contains("evagreen") ? "EvaGreen" : "FAM";

            string hint;
            int needed;
            string[] placeholders;

            if (assay.Contains("single target per channel"))
            {
                hint = "2 targets";
                needed = 2;
                placeholders = new[] { $"{famSignal} / None", "None / HEX" };
            }
            else if (assay.Contains("amplitude multiplex"))
            {
                hint = "4 targets";
                needed = 4;
                placeholders = new[] { $"{famSignal} Lo / None", $"{famSignal} Hi / None", "None / HEX Lo", "None / HEX Hi" };
            }
            else
            {
                hint = "3 targets";
                needed = 3;
                placeholders = new[] { "None / HEX", $"{famSignal} / HEX", $"{famSignal} / None" };
            }

            TargetHintLabel.Text = hint;
            var boxes = new[] { Target1, Target2, Target3, Target4 };
            for (int i = 0; i < boxes.Length; i++)
            {
                boxes[i].Visibility = i < needed ? Visibility.Visible : Visibility.Collapsed;
                if (i < placeholders.Length)
                {
                    boxes[i].SetCurrentValue(TextBoxHelper.WatermarkProperty, placeholders[i]);
                }
            }
        }

        private void ResetPreview()
        {
            _disp.Clear(); _c1.Clear(); _c2.Clear(); _c3.Clear(); _c4.Clear();
            ExportButton.IsEnabled = false;
            PlateScroll.Visibility = Visibility.Collapsed;
            PlateGrid.Children.Clear();
            PlateGrid.RowDefinitions.Clear();
            PlateGrid.ColumnDefinitions.Clear();
            DropPrompt.Visibility = Visibility.Visible;

            // Relax min/max when empty
            this.MinWidth = 400; this.MinHeight = 300;
            this.MaxWidth = double.PositiveInfinity; this.MaxHeight = double.PositiveInfinity;
        }

        private void BuildGrid()
        {
            PlateGrid.Children.Clear();
            PlateGrid.RowDefinitions.Clear();
            PlateGrid.ColumnDefinitions.Clear();

            // 1 header row + 8 rows
            for (int r = 0; r < 9; r++) PlateGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            // 1 header col + 12 cols
            for (int c = 0; c < 13; c++) PlateGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            // Header corner
            AddCell("", 0, 0, isHeader: true);
            // Column headers 01..12
            for (int c = 1; c <= 12; c++)
            {
                AddCell(c.ToString("D2"), 0, c, isHeader: true);
            }
            // Rows A..H
            var rows = new[] { "A","B","C","D","E","F","G","H" };
            for (int r = 0; r < 8; r++)
            {
                AddCell(rows[r], r + 1, 0, isHeader: true);
                for (int c = 1; c <= 12; c++)
                {
                    var idx = (c - 1) * 8 + r; // column-major
                    var n1 = idx < _c1.Count ? _c1[idx] : (idx < _disp.Count ? _disp[idx] : "");
                    var n2 = idx < _c2.Count ? _c2[idx] : "";
                    var n3 = idx < _c3.Count ? _c3[idx] : "";
                    var parts = new List<string>();
                    if (!string.IsNullOrWhiteSpace(n1)) parts.Add(n1);
                    if (!string.IsNullOrWhiteSpace(n2)) parts.Add(n2);
                    if (!string.IsNullOrWhiteSpace(n3)) parts.Add(n3);
                    var text = string.Join("\n", parts);
                    AddCell(text, r + 1, c, isHeader: false);
                }
            }
        }

        private void AddCell(string text, int row, int col, bool isHeader)
        {
            var border = new Border
            {
                BorderBrush = (Brush)FindResource("BorderBrush"),
                BorderThickness = new Thickness(1),
                Margin = new Thickness(0),
                Padding = new Thickness(6, 4, 6, 4)
            };
            var tb = new TextBlock
            {
                Text = text,
                TextAlignment = TextAlignment.Center,
                Foreground = (Brush)FindResource("TextBrush"),
                FontWeight = isHeader ? FontWeights.Bold : FontWeights.Normal,
                FontSize = isHeader ? 16 : 9,
                TextWrapping = TextWrapping.Wrap
            };
            border.Width = 69; border.Height = 50;
            border.Margin = new Thickness(2);
            border.Child = tb;
            Grid.SetRow(border, row);
            Grid.SetColumn(border, col);
            PlateGrid.Children.Add(border);
        }

        private async Task LoadSampleNamesAsync(string path)
        {
            _selectedNamesPath = path;
            try
            {
                var pathB64 = Convert.ToBase64String(Encoding.UTF8.GetBytes(path));
                var script = string.Join("\n", new[]
                {
                    "import os, sys, json, base64",
                    $"p = base64.b64decode('{pathB64}').decode('utf-8')",
                    "ext = os.path.splitext(p)[1].lower()",
                    "disp = []; c1=c2=c3=c4=[]",
                    "try:",
                    "    if ext=='.csv':",
                    "        import pandas as pd",
                    "        df = pd.read_csv(p, header=None).fillna('')",
                    "        def col(i): return [str(x).strip() for x in (df.iloc[:,i].tolist() if i < df.shape[1] else [])]",
                    "        c1=col(0); c2=col(1); c3=col(2); c4=col(3)",
                    "    elif ext in ('.xlsx','.xls'):",
                    "        try:",
                    "            import pandas as pd",
                    "            df = pd.read_excel(p, header=None).fillna('')",
                    "            def col(i): return [str(x).strip() for x in (df.iloc[:,i].tolist() if i < df.shape[1] else [])]",
                    "            c1=col(0); c2=col(1); c3=col(2); c4=col(3)",
                    "        except Exception:",
                    "            try:",
                    "                import openpyxl",
                    "                wb = openpyxl.load_workbook(p, data_only=True)",
                    "                ws = wb.active",
                    "                rows = [[(str(v).strip() if v is not None else '') for v in row] for row in ws.iter_rows(values_only=True)]",
                    "                c1 = [row[0] if len(row)>0 else '' for row in rows]",
                    "                c2 = [row[1] if len(row)>1 else '' for row in rows]",
                    "                c3 = [row[2] if len(row)>2 else '' for row in rows]",
                    "                c4 = [row[3] if len(row)>3 else '' for row in rows]",
                    "            except Exception as e2:",
                    "                print('ERROR:'+str(e2))",
                    "                sys.exit(1)",
                    "    else:",
                    "        print('ERROR:Unsupported file type')",
                    "        sys.exit(1)",
                    "    n=max(len(c1),len(c2),len(c3),len(c4),0)",
                    "    def pad(lst): return (lst + ['']*(n-len(lst)))[:n]",
                    "    c1,c2,c3,c4 = pad(c1),pad(c2),pad(c3),pad(c4)",
                    "    def combine(a,b,c):",
                    "        parts=[x for x in [a,b,c] if str(x).strip()!='']",
                    "        return ' | '.join(parts)",
                    "    disp=[combine(a,b,c) for a,b,c in zip(c1,c2,c3)]",
                    "    print('NAMES:'+json.dumps({'disp':disp,'c1':c1,'c2':c2,'c3':c3,'c4':c4}))",
                    "except Exception as e:",
                    "    print('ERROR:'+str(e))",
                    "    sys.exit(1)"
                });

                var result = await _python.ExecutePythonScript(script);
                var outText = (result.Output ?? string.Empty) + "\n" + (result.Error ?? string.Empty);
                var idx = outText.IndexOf("NAMES:");
                if (idx >= 0)
                {
                    var json = outText.Substring(idx + 6).Trim();
                    var doc = JsonDocument.Parse(json).RootElement;
                    _disp = new List<string>(); _c1 = new List<string>(); _c2 = new List<string>(); _c3 = new List<string>(); _c4 = new List<string>();
                    foreach (var v in doc.GetProperty("disp").EnumerateArray()) _disp.Add(v.GetString() ?? "");
                    foreach (var v in doc.GetProperty("c1").EnumerateArray()) _c1.Add(v.GetString() ?? "");
                    foreach (var v in doc.GetProperty("c2").EnumerateArray()) _c2.Add(v.GetString() ?? "");
                    foreach (var v in doc.GetProperty("c3").EnumerateArray()) _c3.Add(v.GetString() ?? "");
                    foreach (var v in doc.GetProperty("c4").EnumerateArray()) _c4.Add(v.GetString() ?? "");

                    DropPrompt.Visibility = Visibility.Collapsed;
                    PlateScroll.Visibility = Visibility.Visible;
                    BuildGrid();
                    ExportButton.IsEnabled = _disp.Count > 0;

                    // Lock window size once preview is visible
                    this.MinWidth = 1000; this.MinHeight = 605;
                    this.MaxWidth = 1000; this.MaxHeight = 605;
                }
                else if (outText.Contains("ERROR:"))
                {
                    var msg = outText.Substring(outText.IndexOf("ERROR:")).Trim();
                    MessageBox.Show($"Failed to parse names file.\n\n{msg}", "Template Creator", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
                else
                {
                    MessageBox.Show("Failed to parse names file.", "Template Creator", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading names: {ex.Message}", "Template Creator", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void ExportButton_Click(object sender, RoutedEventArgs e)
        {
            if (_disp.Count == 0) return;

            var dlg = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "CSV Files (*.csv)|*.csv",
                FileName = _selectedNamesPath != null ? System.IO.Path.GetFileNameWithoutExtension(_selectedNamesPath) + ".csv" : "plate_template.csv"
            };
            var last = Settings.Default.LastDir_TemplateCreator_Export;
            if (!string.IsNullOrWhiteSpace(last) && Directory.Exists(last)) dlg.InitialDirectory = last;
            if (dlg.ShowDialog(this) != true) return;
            Settings.Default.LastDir_TemplateCreator_Export = System.IO.Path.GetDirectoryName(dlg.FileName) ?? string.Empty;
            Settings.Default.Save();

            var supermix = SupermixCombo.SelectedItem as string ?? "ddPCR Supermix for Probes (No dUTP)";
            var assay = AssayCombo.SelectedItem as string ?? "Probe Mix Triplex";
            var experiment = ExperimentCombo.SelectedItem as string ?? "Copy Number Variation (CNV)";
            var sampleType = "Unknown";
            var targets = new[] { RealTextOrEmpty(Target1), RealTextOrEmpty(Target2), RealTextOrEmpty(Target3), RealTextOrEmpty(Target4) };

            try
            {
                string ToJSON(List<string> arr) => JsonSerializer.Serialize(arr);
                var namesJSON = ToJSON(_disp);
                var names2JSON = ToJSON(_c2);
                var names3JSON = ToJSON(_c3);
                var names4JSON = ToJSON(_c4);
                var targetsJSON = JsonSerializer.Serialize(targets);
                string B64(string s) => Convert.ToBase64String(Encoding.UTF8.GetBytes(s));
                var namesB64 = B64(namesJSON);
                var names2B64 = B64(names2JSON);
                var names3B64 = B64(names3JSON);
                var names4B64 = B64(names4JSON);
                var targetsB64 = B64(targetsJSON);
                var escSupermix = supermix.Replace("'", "\\'");
                var escAssay = assay.Replace("'", "\\'");
                var escExperiment = experiment.Replace("'", "\\'");
                var escSampleType = sampleType.Replace("'", "\\'");
                var outPathJson = JsonSerializer.Serialize(dlg.FileName);

                var outPathB64 = Convert.ToBase64String(Encoding.UTF8.GetBytes(dlg.FileName));
                var py = string.Join("\n", new[]
                {
                    "import sys, os, json, csv, datetime, base64",
                    $"names = json.loads(base64.b64decode('{namesB64}').decode('utf-8'))",
                    $"names2 = json.loads(base64.b64decode('{names2B64}').decode('utf-8'))",
                    $"names3 = json.loads(base64.b64decode('{names3B64}').decode('utf-8'))",
                    $"names4 = json.loads(base64.b64decode('{names4B64}').decode('utf-8'))",
                    $"targets = [t for t in json.loads(base64.b64decode('{targetsB64}').decode('utf-8')) if t]",
                    $"supermix = '{escSupermix}'",
                    $"assay = '{escAssay}'",
                    $"experiment = '{escExperiment}'",
                    $"sample_type = '{escSampleType}'",
                    $"out_path = base64.b64decode('{outPathB64}').decode('utf-8')",
                    "def header():",
                    "    now = datetime.datetime.now()",
                    "    return [[\"ddplate - DO NOT MODIFY THIS LINE\", \"Version=1\",",
                    "             \"ApplicationName=QX Manager Standard Edition\", \"ApplicationVersion=2.3.0.32\",",
                    "             \"ApplicationEdition=ResearchEmbedded\", \"User=\\\\\\\\QX User\",",
                    "             f\"CreatedDate={now.strftime('%m/%d/%Y %H:%M:%S')}\", \"\"],",
                    "            [\"\"], [\"PlateSize=GCR96\"], [\"PlateNotes=\"],",
                    "            [\"Well\",\"Perform Droplet Reading\",\"ExperimentType\",\"Sample description 1\",",
                    "             \"Sample description 2\",\"Sample description 3\",\"Sample description 4\",",
                    "             \"SampleType\",\"SupermixName\",\"AssayType\",\"TargetName\",\"TargetType\",",
                    "             \"Signal Ch1\",\"Signal Ch2\",\"Reference Copies\",\"Well Notes\",\"Plot?\",",
                    "             \"RdqConversionFactor\"]]",
                    "def rows_for_well(well_id, name, n2, n3, n4):",
                    "    base = [well_id, \"Yes\", experiment, name, n2, n3, n4, sample_type, supermix, assay]",
                    "    at = assay.lower()",
                    "    if 'single target per channel' in at: count = 2",
                    "    elif 'amplitude multiplex' in at: count = 4",
                    "    else: count = 3",
                    "    chosen = targets[:count]",
                    "    while len(chosen) < count: chosen.append(f'Target{len(chosen)+1}')",
                    "    rows = []",
                    "    fam_signal = 'EvaGreen' if 'evagreen' in supermix.lower() else 'FAM'",
                    "    if count == 2: patterns = [(f'{fam_signal}', 'None'), ('None', 'HEX')]",
                    "    elif count == 3: patterns = [('None','HEX'), (f'{fam_signal}','HEX'), (f'{fam_signal}','None')]",
                    "    else: patterns = [(f'{fam_signal} Lo','None'), (f'{fam_signal} Hi','None'), ('None','HEX Lo'), ('None','HEX Hi')]",
                    "    for i in range(count):",
                    "        target_name = chosen[i]",
                    "        sig1, sig2 = patterns[i]",
                    "        row = base + [target_name, \"Unknown\", sig1, sig2, \"\", \"\", \"False\", \"\"]",
                    "        rows.append(row)",
                    "    return rows",
                    "lines = header()",
                    "for row_idx, row_letter in enumerate('ABCDEFGH'):",
                    "    for col in range(1,13):",
                    "        well = f'{row_letter}{col:02d}'",
                    "        idx = (col-1)*8 + row_idx",
                    "        if idx < len(names):",
                    "            nm = str(names[idx])",
                    "            n2 = str(names2[idx]) if idx < len(names2) else ''",
                    "            n3 = str(names3[idx]) if idx < len(names3) else ''",
                    "            n4 = str(names4[idx]) if idx < len(names4) else ''",
                    "            lines.extend(rows_for_well(well, nm, n2, n3, n4))",
                    "        else:",
                    "            lines.append([well, 'No'] + ['']*16)",
                    "with open(out_path,'w',newline='') as f: csv.writer(f).writerows(lines)",
                    "print('EXPORTED:'+out_path)"
                });

                var exec = await _python.ExecutePythonScript(py);
                if (exec.Output != null && exec.Output.Contains("EXPORTED:"))
                {
                    try
                    {
                        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                        {
                            FileName = "explorer",
                            Arguments = $"/select,\"{dlg.FileName}\"",
                            UseShellExecute = true
                        });
                    }
                    catch { }
                }
                else
                {
                    MessageBox.Show("Export failed. See logs for details.", "Template Creator", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Export failed: {ex.Message}", "Template Creator", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void HelpButton_Click(object sender, RoutedEventArgs e)
        {
            // Toggle the contextual help popup below the button (match main window behavior)
            if (this.FindName("HelpPopup") is System.Windows.Controls.Primitives.Popup pop)
            {
                pop.IsOpen = !pop.IsOpen;
            }
        }

        private void DropPrompt_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            var dlg = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Sample Files (*.csv;*.xlsx;*.xls)|*.csv;*.xlsx;*.xls|All Files (*.*)|*.*"
            };
            var last = Settings.Default.LastDir_TemplateCreator_Input;
            if (!string.IsNullOrWhiteSpace(last) && Directory.Exists(last)) dlg.InitialDirectory = last;
            if (dlg.ShowDialog(this) == true)
            {
                Settings.Default.LastDir_TemplateCreator_Input = System.IO.Path.GetDirectoryName(dlg.FileName) ?? string.Empty;
                Settings.Default.Save();
                _ = LoadSampleNamesAsync(dlg.FileName);
            }
        }

        private void DropPrompt_DragOver(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                e.Effects = DragDropEffects.Copy;
            }
            else
            {
                e.Effects = DragDropEffects.None;
            }
            e.Handled = true;
        }

        private void DropPrompt_Drop(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                var files = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (files.Length > 0)
                {
                    Settings.Default.LastDir_TemplateCreator_Input = System.IO.Path.GetDirectoryName(files[0]) ?? string.Empty;
                    Settings.Default.Save();
                    _ = LoadSampleNamesAsync(files[0]);
                }
            }
        }
    }

    // Helper for watermark placeholder text in TextBox (simple attached property)
    public static class TextBoxHelper
    {
        public static readonly DependencyProperty WatermarkProperty = DependencyProperty.RegisterAttached(
            "Watermark", typeof(string), typeof(TextBoxHelper), new PropertyMetadata(string.Empty, OnWatermarkChanged));

        public static string GetWatermark(DependencyObject obj) => (string)obj.GetValue(WatermarkProperty);
        public static void SetWatermark(DependencyObject obj, string value) => obj.SetValue(WatermarkProperty, value);

        private static void OnWatermarkChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (d is TextBox tb)
            {
                tb.Loaded -= Tb_Loaded; tb.Loaded += Tb_Loaded;
                tb.TextChanged -= Tb_TextChanged; tb.TextChanged += Tb_TextChanged;
                UpdateWatermark(tb);
            }
        }

        private static void Tb_Loaded(object sender, RoutedEventArgs e) => UpdateWatermark((TextBox)sender);
        private static void Tb_TextChanged(object sender, TextChangedEventArgs e) => UpdateWatermark((TextBox)sender);

        private static void UpdateWatermark(TextBox tb)
        {
            var wm = GetWatermark(tb);
            if (string.IsNullOrEmpty(tb.Text) && !string.IsNullOrEmpty(wm))
            {
                tb.Foreground = Brushes.Gray;
                tb.Text = wm;
                tb.GotKeyboardFocus -= Tb_GotKeyboardFocus; tb.GotKeyboardFocus += Tb_GotKeyboardFocus;
                tb.LostKeyboardFocus -= Tb_LostKeyboardFocus; tb.LostKeyboardFocus += Tb_LostKeyboardFocus;
            }
            else if (tb.Foreground == Brushes.Gray && tb.Text == wm)
            {
                // keep placeholder
            }
            else if (tb.Foreground == Brushes.Gray && tb.Text != wm)
            {
                tb.Foreground = (Brush)Application.Current.FindResource("TextBrush");
            }
        }

        private static void Tb_GotKeyboardFocus(object sender, KeyboardFocusChangedEventArgs e)
        {
            var tb = (TextBox)sender;
            var wm = GetWatermark(tb);
            if (tb.Foreground == Brushes.Gray && tb.Text == wm)
            {
                tb.Text = string.Empty;
                tb.Foreground = (Brush)Application.Current.FindResource("TextBrush");
            }
        }

        private static void Tb_LostKeyboardFocus(object sender, KeyboardFocusChangedEventArgs e)
        {
            var tb = (TextBox)sender;
            var wm = GetWatermark(tb);
            if (string.IsNullOrEmpty(tb.Text))
            {
                tb.Foreground = Brushes.Gray;
                tb.Text = wm;
            }
        }
    }
}
